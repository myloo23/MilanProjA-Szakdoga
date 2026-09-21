# A Terraform és a provider verziójának rögzítése. Ugyanaz a logika, mint a
# requirements.txt hash-lockolásánál: ha a provider holnap kiad egy új főverziót,
# a `terraform init` ne húzza be magától, mert attól a `plan` megváltozhat anélkül,
# hogy egy sort is írtál volna.
terraform {
  required_version = ">= 1.9.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  # Az állapot (state) helyben, ebben a könyvtárban marad. Távoli state-tároló
  # (Azure Storage backend) csapatmunka esetén kell; egy szerzőnél fölösleges
  # bonyolítás, és a dolgozat 7. fejezetébe tartozik.
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}
