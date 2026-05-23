data "oci_core_subnet" "target" {
  subnet_id = var.subnet_id
}

resource "oci_core_network_security_group" "leoai" {
  compartment_id = var.compartment_id
  vcn_id         = data.oci_core_subnet.target.vcn_id
  display_name   = "${var.instance_display_name}-nsg"
  defined_tags   = var.defined_tags
  freeform_tags  = var.freeform_tags
}

resource "oci_core_network_security_group_security_rule" "leoai_ingress_ssh" {
  network_security_group_id = oci_core_network_security_group.leoai.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.laptop_ingress_cidr
  source_type               = "CIDR_BLOCK"

  tcp_options {
    destination_port_range {
      min = 22
      max = 22
    }
  }
}

resource "oci_core_network_security_group_security_rule" "leoai_ingress_api" {
  network_security_group_id = oci_core_network_security_group.leoai.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.laptop_ingress_cidr
  source_type               = "CIDR_BLOCK"

  tcp_options {
    destination_port_range {
      min = var.leoai_api_port
      max = var.leoai_api_port
    }
  }
}

resource "oci_core_network_security_group_security_rule" "leoai_egress_all" {
  network_security_group_id = oci_core_network_security_group.leoai.id
  direction                 = "EGRESS"
  protocol                  = "all"
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
}

resource "oci_core_instance" "leoai" {
  availability_domain = var.availability_domain
  compartment_id      = var.compartment_id
  display_name        = var.instance_display_name
  shape               = var.instance_shape

  dynamic "shape_config" {
    for_each = can(regex("Flex", var.instance_shape)) ? [1] : []
    content {
      ocpus         = var.shape_ocpus
      memory_in_gbs = var.shape_memory_gbs
    }
  }

  create_vnic_details {
    subnet_id        = var.subnet_id
    assign_public_ip = var.assign_public_ip
    nsg_ids          = concat(var.nsg_ids, [oci_core_network_security_group.leoai.id])
  }

  metadata = {
    ssh_authorized_keys = trimspace(file(var.ssh_public_key_path))
  }

  source_details {
    source_type = "image"
    source_id   = var.image_id
  }

  defined_tags  = var.defined_tags
  freeform_tags = var.freeform_tags
}

resource "local_file" "ansible_inventory" {
  count = var.generate_ansible_inventory ? 1 : 0

  filename = "${path.module}/../ansible/inventory/hosts.ini"
  content  = <<-EOT
[leoai]
${oci_core_instance.leoai.public_ip} ansible_user=${var.ansible_ssh_user}${var.ansible_ssh_private_key_file != "" ? " ansible_ssh_private_key_file=${var.ansible_ssh_private_key_file}" : ""}
EOT
}
