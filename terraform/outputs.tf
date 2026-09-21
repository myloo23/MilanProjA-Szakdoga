output "public_ip" {
  description = "A gép publikus IP-címe."
  value       = azurerm_public_ip.main.ip_address
}

output "ssh_command" {
  description = "Belépés a gépre."
  value       = "ssh ${var.admin_username}@${azurerm_public_ip.main.ip_address}"
}

output "kubeconfig_command" {
  description = <<-EOT
    A fürt kubeconfigjának lehozása a laptopra. A k3s a fájlban 127.0.0.1-et
    ír, ami a gépen belül helyes, kívülről nem — ezért kell a csere.
  EOT
  value = join(" && ", [
    "scp ${var.admin_username}@${azurerm_public_ip.main.ip_address}:/etc/rancher/k3s/k3s.yaml ~/.kube/szakdoga-azure.yaml",
    "sed -i '' 's|127.0.0.1|${azurerm_public_ip.main.ip_address}|' ~/.kube/szakdoga-azure.yaml",
    "KUBECONFIG=~/.kube/szakdoga-azure.yaml kubectl get nodes"
  ])
}
