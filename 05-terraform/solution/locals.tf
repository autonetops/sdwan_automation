locals {
  prefix = var.student

  policy_file = yamldecode(file("${path.module}/../configs/policy_objects.yaml"))
  application_list = {
    for app in local.policy_file.sdwan.policy_objects.application_list : app.name => app
  }
}
