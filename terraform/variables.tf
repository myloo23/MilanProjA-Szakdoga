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
    Az Azure-régió. Nem ízlés kérdése, hanem lekérdezés eredménye
    (szakdolgozat/bizonyitek/02-regio-es-meret-valasztas.md):
      1. Az Azure for Students előfizetésre régiókorlátozó szabály vonatkozik
         ("Allowed resource deployment regions"); csak belgiumcentral,
         austriaeast, francecentral, swedencentral és spaincentral engedett.
         A westeurope 403 RequestDisallowedByAzure hibát adott.
      2. Az öt régióban a méretek túlnyomó része NotAvailableForSubscription
         tiltás alatt áll; az austriaeast és a francecentral 409
         SkuNotAvailable hibát adott B2ms-re és B2s_v2-re is.
      3. Az `az vm list-skus --all` szerint egyetlen tiltás nélküli kombináció
         van: swedencentral + Standard_B2s_v2.
    Az érték nem titok, ezért itt, a verziókezelt alapértékek között a helye:
    így egy tiszta klónból indított `apply` is a mért gépet hozza létre.
  EOT
  type        = string
  default     = "swedencentral"
}

variable "prefix" {
  description = <<-EOT
    Minden erőforrás neve ezzel kezdődik, hogy a portálon összetartozzanak.
    "szakdoga2", mert a régió- és méretpróbák során a "szakdoga-rg" csoportot
    többször törölni és azonos néven újra létrehozni kellett, és ettől az Azure
    vezérlősíkja és a state szétcsúszott; a tiszta megoldás az új névtér volt.
  EOT
  type        = string
  default     = "szakdoga2"
}

variable "vm_size" {
  description = <<-EOT
    A virtuális gép mérete: Standard_B2s_v2 (2 vCPU, 8 GB). Ezen az egy gépen
    fut a k3s fürt, a Gitea, a runner, a registry és maguk a buildek is. Az
    előfizetésen ez az egyetlen használható méret (lásd a location leírását).
    A B-sorozat CPU-kredites: tartós terhelés alatt fojthat, ezt a dolgozat a
    mérés érvényességénél tárgyalja.
  EOT
  type        = string
  default     = "Standard_B2s_v2"
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
    A mérőgép az 1-es zónában jött létre; ez az alapérték, hogy a tiszta
    klónból indított `apply` is ugyanazt a gépet írja le. Egy csomópont, egy
    zóna (ADR-0008).
  EOT
  type        = string
  default     = "1"
}
