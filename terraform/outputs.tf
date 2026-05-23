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

output "effective_subnet_id" {
  description = "Subnet efetivamente usada pela instancia"
  value       = var.use_private_subnet_with_nat_sgw ? oci_core_subnet.leoai_private[0].id : var.subnet_id
}

output "nat_gateway_id" {
  description = "OCID do NAT Gateway criado (quando habilitado)"
  value       = var.use_private_subnet_with_nat_sgw ? oci_core_nat_gateway.leoai[0].id : null
}

output "service_gateway_id" {
  description = "OCID do Service Gateway criado (quando habilitado)"
  value       = var.use_private_subnet_with_nat_sgw ? oci_core_service_gateway.leoai[0].id : null
}
