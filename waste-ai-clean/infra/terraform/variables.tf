variable "region" {
  default = "eu-west-3"
}

variable "project" {
  default = "waste-ai"
}

variable "db_username" {
  default = "wasteadmin"
}

variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}
