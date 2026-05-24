variable "oci_region" {
  description = "Regiao OCI (ex.: eu-madrid-1)"
  type        = string
}

variable "oci_config_profile" {
  description = "Profile no ~/.oci/config (ex.: DEFAULT, JNB)"
  type        = string
  default     = "DEFAULT"
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

variable "use_private_subnet_with_nat_sgw" {
  description = "Quando true, cria subnet privada no VCN alvo com NAT Gateway + Service Gateway"
  type        = bool
  default     = true
}

variable "create_service_gateway" {
  description = "Quando true, cria Service Gateway no VCN alvo (independente do modo privado/publico)"
  type        = bool
  default     = true

  validation {
    condition     = var.use_private_subnet_with_nat_sgw ? var.create_service_gateway : true
    error_message = "Quando use_private_subnet_with_nat_sgw=true, create_service_gateway tambem deve ser true."
  }
}

variable "private_subnet_cidr" {
  description = "CIDR da subnet privada a ser criada quando use_private_subnet_with_nat_sgw=true"
  type        = string
  default     = "10.50.20.0/24"
}

variable "private_subnet_display_name" {
  description = "Nome da subnet privada criada para o LeoAI"
  type        = string
  default     = "subnet-private-leoai"
}

variable "private_subnet_dns_label" {
  description = "DNS label da subnet privada (1-15 chars alfanumericos)"
  type        = string
  default     = "leoaipvt"
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

variable "laptop_ingress_cidr" {
  description = "CIDR do IP publico autorizado para ingress (ex.: 203.0.113.10/32)"
  type        = string
}

variable "leoai_api_port" {
  description = "Porta TCP da API LeoAI no backend (uvicorn). Usada apenas quando allow_direct_api_ingress=true"
  type        = number
  default     = 8000
}

variable "leoai_http_port" {
  description = "Porta TCP publica HTTP no reverse proxy"
  type        = number
  default     = 80
}

variable "leoai_https_port" {
  description = "Porta TCP publica HTTPS no reverse proxy"
  type        = number
  default     = 443
}

variable "allow_direct_api_ingress" {
  description = "Quando true, permite acesso direto ao backend uvicorn (leoai_api_port). Em producao deve ser false."
  type        = bool
  default     = false
}

variable "ansible_ssh_user" {
  description = "Usuario SSH padrao da imagem (ex.: opc, ubuntu)"
  type        = string
  default     = "opc"
}

variable "ansible_ssh_private_key_file" {
  description = "Caminho local da chave privada SSH para o Ansible"
  type        = string
  default     = ""
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
