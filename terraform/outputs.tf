output "instance_id" {
  description = "OCID da instancia criada"
  value       = oci_core_instance.leoai.id
}

output "instance_public_ip" {
  description = "IP publico da instancia"
  value       = oci_core_instance.leoai.public_ip
}

output "instance_private_ip" {
  description = "IP privado da instancia"
  value       = oci_core_instance.leoai.private_ip
}

output "ansible_inventory_file" {
  description = "Arquivo de inventario gerado para o Ansible"
  value       = var.generate_ansible_inventory ? local_file.ansible_inventory[0].filename : null
}
