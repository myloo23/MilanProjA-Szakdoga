variable "subscription_id" {
  description = "Az Azure-előfizetés azonosítója (az `az account show --query id -o tsv` adja meg)."
  type        = string
}

variable "allowed_cidr" {
  description = <<-EOT
    Az egyetlen hálózat, ahonnan a gép elérhető, CIDR-alakban: "1.2.3.4/32".
    A saját publikus IP-címed, nem a gép belső címe. Ha vált (másik hálózat,
    a szolgáltató új címet ad), írd át és futtass `terraform apply`-t — a
    tűzfalszabály frissül, a gép megmarad.
  EOT
  type        = string

  validation {
    condition     = can(cidrhost(var.allowed_cidr, 0))
    error_message = "Érvényes CIDR kell, például 84.0.0.1/32 — a puszta IP-cím nem elég."
  }
}

variable "location" {
  description = <<-EOT
    Az Azure-régió. Az Azure for Students előfizetésre régiókorlátozó szabály
    vonatkozik ("Allowed resource deployment regions"), ami a westeurope-ot
    nem engedi: az apply 403 RequestDisallowedByAzure hibával áll meg. Az
    engedélyezett listát az
      az policy assignment list --disable-scope-strict-match
    adja meg. A legközelebbi engedélyezett régió (austriaeast) kicsi és új:
    ott a B2ms létrehozása 409 SkuNotAvailable hibával állt meg kapacitáshiány
    miatt, amit az `az vm list-skus` nem jelez előre. Az alapérték ezért egy
    nagy, régi régió.
  EOT
  type        = string
  default     = "austriaeast"
}

variable "prefix" {
  description = "Minden erőforrás neve ezzel kezdődik, hogy a portálon összetartozzanak."
  type        = string
  default     = "szakdoga"
}

variable "vm_size" {
  description = <<-EOT
    A virtuális gép mérete. A B2ms (2 vCPU, 8 GB) azért kell, mert ezen az egy
    gépen fut a k3s fürt, a Gitea, a runner, a registry és maguk a buildek is.
    A B-sorozat CPU-kredites: tartós terhelés alatt fojt. Ha ez a mérési
    adatokban megjelenik (a hosszú futások szórása nő), a Standard_D2s_v5 a
    következő lépés — és ezt a dolgozatban meg kell említeni.
  EOT
  type        = string
  default     = "Standard_B2ms"
}

variable "admin_username" {
  description = "A gép rendszergazdai felhasználója. Jelszavas belépés nincs, csak SSH-kulcs."
  type        = string
  default     = "azureuser"
}

variable "ssh_public_key_path" {
  description = "A publikus SSH-kulcsod útvonala. A privát kulcs sosem hagyja el a gépedet."
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "os_disk_size_gb" {
  description = "A rendszerlemez mérete. A konténerképek és a registry ezen laknak."
  type        = number
  default     = 48
}

variable "zone" {
  description = <<-EOT
    Rendelkezésre állási zóna ("1", "2" vagy "3"), vagy null a régió közös
    készletéből való foglaláshoz. Az Azure a kapacitást zónánként tartja
    nyilván: ha a régió általános készlete kifogyott (409 SkuNotAvailable,
    "Capacity Restrictions"), egy konkrét zóna kérése még sikerülhet.
    A dolgozat szempontjából közömbös, melyik zónában fut a gép — egy
    csomópont, egy zóna (ADR-0008).
  EOT
  type        = string
  default     = null
}
