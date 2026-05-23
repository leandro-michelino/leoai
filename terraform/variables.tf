variable "oci_region" {
  description = "Regiao OCI (ex.: eu-madrid-1)"
  type        = string
}

variable "compartment_id" {
  description = "OCID do compartment"
  type        = string
}

variable "availability_domain" {
  description = "Availability Domain (ex.: kIdk:EU-MADRID-1-AD-1)"
  type        = string
}

variable "subnet_id" {
  description = "OCID da subnet onde a instancia sera criada"
  type        = string
}

variable "image_id" {
  description = "OCID da imagem da instancia"
  type        = string
}

variable "instance_shape" {
  description = "Shape da instancia"
  type        = string
  default     = "VM.Standard.E4.Flex"
}

variable "shape_ocpus" {
  description = "Numero de OCPUs para shapes Flex"
  type        = number
  default     = 1
}

variable "shape_memory_gbs" {
  description = "Memoria (GB) para shapes Flex"
  type        = number
  default     = 8
}

variable "instance_display_name" {
  description = "Nome da instancia"
  type        = string
  default     = "leoai-app"
}

variable "ssh_public_key_path" {
  description = "Caminho local da chave publica SSH"
  type        = string
}

variable "assign_public_ip" {
  description = "Atribuir IP publico a VNIC primaria"
  type        = bool
  default     = true
}

variable "nsg_ids" {
  description = "Lista de NSG OCIDs para a VNIC"
  type        = list(string)
  default     = []
}

variable "ansible_ssh_user" {
  description = "Usuario SSH padrao da imagem (ex.: opc, ubuntu)"
  type        = string
  default     = "opc"
}

variable "generate_ansible_inventory" {
  description = "Gerar automaticamente ansible/inventory/hosts.ini"
  type        = bool
  default     = true
}

variable "defined_tags" {
  description = "Defined tags OCI"
  type        = map(string)
  default     = {}
}

variable "freeform_tags" {
  description = "Freeform tags OCI"
  type        = map(string)
  default = {
    project = "leoai"
    managed = "terraform"
  }
}
