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
    nsg_ids          = var.nsg_ids
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
${oci_core_instance.leoai.public_ip} ansible_user=${var.ansible_ssh_user}
EOT
}
