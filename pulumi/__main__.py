import os
import pulumi
import pulumi_yandex as yandex

config = pulumi.Config()

zone = config.get("zone") or "ru-central1-a"
folder_id = config.require("folderId")
image_id = config.require("imageId")
my_ip = config.require("myIp")
public_key_path = os.path.expanduser(config.require("publicKeyPath"))

# Secret
token = config.require_secret("token")

# Provider
yc_provider = yandex.Provider(
    "yc",
    zone=zone,
    folder_id=folder_id,
    token=token,
)

opts = pulumi.ResourceOptions(provider=yc_provider)

# Network
network = yandex.VpcNetwork(
    "lab-network",
    name="lab-network",
    opts=opts,
)

subnet = yandex.VpcSubnet(
    "lab-subnet",
    name="lab-subnet",
    zone=zone,
    network_id=network.id,
    v4_cidr_blocks=["10.10.0.0/24"],
    opts=opts,
)

# Security Group
sg = yandex.VpcSecurityGroup(
    "lab-sg",
    name="lab-sg",
    network_id=network.id,
    opts=opts,
)

ssh_rule = yandex.VpcSecurityGroupRule(
    "lab-sg-ssh",
    security_group_binding=sg.id,
    direction="ingress",
    protocol="TCP",
    v4_cidr_blocks=[my_ip],
    port=22,
    opts=opts,
)


http_rule = yandex.VpcSecurityGroupRule(
    "lab-sg-http",
    security_group_binding=sg.id,
    direction="ingress",
    protocol="TCP",
    v4_cidr_blocks=["0.0.0.0/0"],
    port=80,
    opts=opts,
)

app_rule = yandex.VpcSecurityGroupRule(
    "lab-sg-5000",
    security_group_binding=sg.id,
    direction="ingress",
    protocol="TCP",
    v4_cidr_blocks=["0.0.0.0/0"],
    port=5000,
    opts=opts,
)

egress_rule = yandex.VpcSecurityGroupRule(
    "lab-sg-egress",
    security_group_binding=sg.id,
    direction="egress",
    protocol="ANY",
    v4_cidr_blocks=["0.0.0.0/0"],
    opts=opts,
)

# SSH public key
with open(public_key_path, "r", encoding="utf-8") as f:
    public_key = f.read().strip()

# Compute Instance
vm = yandex.ComputeInstance(
    "lab-vm",
    name="lab-vm",
    platform_id="standard-v2",
    resources=yandex.ComputeInstanceResourcesArgs(
        cores=2,
        memory=1,
        core_fraction=20,
    ),
    boot_disk=yandex.ComputeInstanceBootDiskArgs(
        initialize_params=yandex.ComputeInstanceBootDiskInitializeParamsArgs(
            image_id=image_id,
            size=10,
        )
    ),
    network_interfaces=[
        yandex.ComputeInstanceNetworkInterfaceArgs(
            subnet_id=subnet.id,
            nat=True,
            security_group_ids=[sg.id],
        )
    ],
    metadata={
        "ssh-keys": f"ubuntu:{public_key}",
    },
    opts=opts,
)

# Output public IP
public_ip = vm.network_interfaces.apply(lambda nis: nis[0].nat_ip_address)
pulumi.export("public_ip", public_ip)
