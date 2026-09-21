# A mérés célkörnyezete Terraformmal

Ez a könyvtár hozza létre azt az egyetlen Azure-beli virtuális gépet, amin a
mérés mindkét oldala fut: a k3s fürt, és mellette a Gitea, a runner és a
registry. A Terraform hatóköre itt ér véget — az alkalmazást a Helm telepíti
(ADR-0008, ADR-0009).

## Egyszeri előkészítés

```bash
brew install terraform azure-cli
az login                                    # böngészőben belépsz
az account show --query id -o tsv           # ez az előfizetés-azonosító
curl -s ifconfig.me                         # ez a publikus IP-címed
ls ~/.ssh/id_ed25519.pub                    # ha nincs: ssh-keygen -t ed25519
```

Aztán:

```bash
cp terraform.tfvars.example terraform.tfvars
```

és töltsd ki a két értéket. Az `allowed_cidr`-be az IP-cím mögé `/32` kell:
`84.0.12.34/32`.

## Létrehozás

```bash
terraform init      # letölti a providert, létrehozza a lock-fájlt
terraform plan      # OLVASD EL: mit akar létrehozni, hány erőforrást
terraform apply
```

A `plan` kimenetének elolvasása nem formaság: ez az a pillanat, amikor még
ingyen derül ki, ha valami mást csinálna, mint amit gondolsz. A dolgozat 4.5
alfejezetébe egy `plan`-részlet jó ábra.

Az `apply` után a gép él, de a cloud-init még dolgozik 2–3 percig. Akkor kész,
ha ez a fájl létezik:

```bash
ssh azureuser@$(terraform output -raw public_ip) 'test -f /var/lib/cloud/instance/k3s-ready && echo kesz'
```

Utána a fürt lehozása a laptopra:

```bash
terraform output -raw kubeconfig_command     # kiírja a három parancsot
```

## A 2.3 pont kész-feltétele

A megvalósítási terv azt kéri, hogy `destroy` + `apply` után **kézi
beavatkozás nélkül** legyen működő fürt. Ezt egyszer csináld végig, és készíts
róla képernyőképet a dolgozatba:

```bash
terraform destroy
terraform apply
# majd újra a k3s-ready ellenőrzés és a kubectl get nodes
```

## Kreditfegyelem

A hallgatói keret 100 USD, és a gép óradíjas. **A gépen belüli `shutdown` nem
állítja le a számlázást** — csak a felszabadítás:

```bash
az vm deallocate -g szakdoga-rg -n szakdoga-vm    # este / hétvégén
az vm start      -g szakdoga-rg -n szakdoga-vm    # amikor dolgozol
```

Felszabadított állapotban a lemez és a publikus IP továbbra is fogy valamennyit,
de a gép ára nem. A mérés napjain nyilván fusson végig.
