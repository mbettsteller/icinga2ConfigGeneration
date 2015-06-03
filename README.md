# icinga2ConfigGeneration
This little scripts are used to automatically generate an icinga2 config from some sort of CMDB. In the current
project, whenever we create a new virtual machine it automatically starts sending metrics to a graphite server.
That is why we can rely on graphite as a CMDB.

## createHostlistFromGraphite
The idea of this script is generating a hostlist with groups. The groups of the servers are based on the naming scheme of
the servers:

functionNNN-project-environment

functionNNN is the function of the machine, e.g. apache001
project is the projectname or division the machine belongs to, e.g. sales
environment is your environment, e.g. qa, dev or prod

Lets say your graphite gets pumped with metrics by collectd unter the /collectd path.
There you have an entry "apache001-sales-production_somwhere_fancy_com"

Then you call:

./generateHostsFromGraphite.py --graphite=https://yourGraphiteServer --path=collectd.* -b=(localhost+)|(template+) -m=(somewhere_fancy_com+)
-c=/etc/icinga2/conf.d/serversFromGraphite

That would create two files:
/etc/icinga2/conf.d/serversFromGraphiteHosts.conf
/etc/icinga2/conf.d/serversFromGraphiteGroups.conf

Containing groups "apache", "sales", "production" and "fromGraphite" in the /etc/icinga2/conf.d/serversFromGraphiteGroups.conf
and in /etc/icinga2/conf.d/serversFromGraphiteHosts.conf you find a hostobject called "apache001-sales-production"

RegEx Parameters for filtering:
The -b parameter describes a blacklist (e.g. if you have templates or servers that should not be included in the
automatic generation of the config (default is none)).
-m includes everything that matches the pattern (default is everything)

## generateGatewayObjects
I needed those object in an environment to generate gateway objects. Later in the check configuration I use them as
a dependency (no use trying to check your servers and services if the gateway of the VLAN is down...

