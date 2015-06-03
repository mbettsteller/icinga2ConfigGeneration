#!/usr/bin/python
__author__ = 'markus'
template = """
object Host "Gateway_10.10.{OCTET}.1" {{
  import "generic-host"
  check_interval = 30s
  retry_interval = 15s
  max_check_attempts = 5
  vars.generated = "manual"
  address = "10.10.{OCTET}.1"
  vars.serverFunction = "gateway"
  vars.environment = "prod"
}}
"""

octets = range(2, 254)

for (octet) in octets:
    print(
        template.format(OCTET=str(octet))
    )
