# A mérés célkörnyezete: egyetlen virtuális gép és a köré tartozó hálózat.
# A Terraform hatóköre itt ér véget (ADR-0008, D4 döntés): a gépet és a k3s
# telepítését csinálja meg, az alkalmazást nem. Ha az alkalmazást is ez
# telepítené, összemosódna a telepítési lánccal, amit mérni akarunk.

# Minden erőforrás egy csoportban. A `terraform destroy` ezt bontja le, és
# ez a legjobb bizonyíték arra, hogy tényleg kódból van a környezet.
resource "azurerm_resource_group" "main" {
  name     = "${var.prefix}-rg"
  location = var.location
}

# A virtuális hálózat és benne egy alhálózat. Egyetlen gép is hálózatban él:
# az Azure-ban nincs "csak egy gép", a NIC-nek kell egy alhálózat.
resource "azurerm_virtual_network" "main" {
  name                = "${var.prefix}-vnet"
  address_space       = ["10.42.0.0/16"]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_subnet" "main" {
  name                 = "${var.prefix}-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.42.1.0/24"]
}

# A tűzfal. Az Azure alapértelmezése a bejövő forgalomra a tiltás, tehát itt
# csak azt kell felsorolni, ami át mehet — és mindet ugyanarról az egy címről.
resource "azurerm_network_security_group" "main" {
  name                = "${var.prefix}-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  # SSH és a Kubernetes API. A 6443 azért kell, hogy a laptopodról a kubectl
  # elérje a fürtöt; enélkül minden parancshoz be kellene SSH-zni a gépre.
  security_rule {
    name                       = "management-from-my-ip"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_ranges    = ["22", "6443"]
    source_address_prefix      = var.allowed_cidr
    destination_address_prefix = "*"
  }

  # Az alkalmazás (Traefik, 80/443). Szintén csak a saját címedről: az
  # alkalmazásban nincs hitelesítés, publikusan bárki írhatna a jegyzetek
  # táblájába a mérés közben, ami meghamisítaná az eredményt.
  #
  # A Gitea 3000-es portja szándékosan NINCS itt. A platform minden portja a
  # gép 127.0.0.1-es címére kötött (platform/compose.yaml eleje), tehát
  # kívülről ezen a porton semmi nem fogad kapcsolatot; a Gitea felülete
  # SSH-alagúton érhető el (docs/RUNBOOK.md). Korábban itt volt, de a platform
  # átköltöztetése óta nem engedett át semmit — a legkisebb szükséges
  # jogosultság elve szerint ami nem kell, az ne legyen nyitva.
  security_rule {
    name                       = "http-from-my-ip"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_ranges    = ["80", "443"]
    source_address_prefix      = var.allowed_cidr
    destination_address_prefix = "*"
  }
}

# Állandó publikus IP-cím. Azért statikus és nem dinamikus, mert a k3s
# tanúsítványába bele van égetve (lásd cloud-init.yaml, --tls-san), és mert a
# kubeconfig is erre mutat: egy változó cím minden újraindításnál elrontaná.
resource "azurerm_public_ip" "main" {
  name                = "${var.prefix}-ip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_network_interface" "main" {
  name                = "${var.prefix}-nic"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.main.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.main.id
  }
}

# A tűzfal a hálózati kártyához kötődik. Külön erőforrás, mert ugyanaz az NSG
# több kártyához is tartozhatna.
resource "azurerm_network_interface_security_group_association" "main" {
  network_interface_id      = azurerm_network_interface.main.id
  network_security_group_id = azurerm_network_security_group.main.id
}

resource "azurerm_linux_virtual_machine" "main" {
  name                = "${var.prefix}-vm"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  size                = var.vm_size
  admin_username      = var.admin_username

  # Ha meg van adva, a gép ebbe a rendelkezésre állási zónába kerül. Lásd a
  # variables.tf "zone" leírását: kapacitáshiánynál ez a kerülőút.
  zone = var.zone

  network_interface_ids = [azurerm_network_interface.main.id]

  # Jelszavas belépés nincs. Ez az azurerm alapértelmezése is, de kimondva
  # látszik a kódban, és a dolgozatban hivatkozható.
  disable_password_authentication = true

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(pathexpand(var.ssh_public_key_path))
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS"
    disk_size_gb         = var.os_disk_size_gb
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  # A gép indulásakor lefutó szkript. Ettől lesz a fürt is a Terraform
  # eredménye: `destroy` után egy `apply` kézi beavatkozás nélkül ad vissza
  # egy működő k3s fürtöt (a megvalósítási terv 2.3 pontjának kész-feltétele).
  custom_data = base64encode(templatefile("${path.module}/cloud-init.yaml", {
    public_ip      = azurerm_public_ip.main.ip_address
    admin_username = var.admin_username
  }))

  # **A custom_data változása NEM cserélheti le a gépet.** Az azurerm-ben a
  # custom_data „ForceNew" mező: ha a cloud-init.yaml tartalma bármiben eltér
  # attól, amivel a gép létrejött, a következő `apply` a gépet törli és újat
  # hoz létre — lemezzel, fürttel, Giteával, registryvel együtt.
  #
  # Ez 2026-09-30-án megtörtént. A cloud-init.yaml 2026-09-21-én változott (a
  # registries.yaml kivezetése, 2.4), de azt a változást senki nem alkalmazta,
  # mert a gép már futott. Tíz nappal később egy ártatlan NSG-módosítás (az
  # allowed_cidr új otthoni IP-re) `apply`-ja magával vitte a függő cserét is:
  # a gép újra létrejött (virtual_machine_id 29cfc322… → 2fff48cb…), és vele
  # minden, ami nem kódból jön. A mérési bizonyítékanyagot ez nem érintette,
  # mert az a repóban van (szakdolgozat/bizonyitek/), nem a gépen.
  #
  # A cloud-init csak az első induláskor fut le, tehát egy futó gépen a
  # módosítása amúgy sem hatna. Ha a gépet szándékosan új cloud-init-tel kell
  # újraépíteni, az kimondott döntés legyen:
  #   terraform apply -replace=azurerm_linux_virtual_machine.main
  lifecycle {
    ignore_changes = [custom_data]
  }
}
