# CIFv3 DeploymentKit

```bash
$ curl -L https://github.com/csirtgadgets/bearded-avenger-deploymentkit/archive/master.tar.gz > bearded-avenger-deploymentkit.tar.gz
$ cd bearded-avenger-deploymentkit-master
$ sudo bash easybutton.sh
$ sudo service csirtg-smrt stop
$ sudo su - cif
$ csirtg-smrt --client cif --fireball -r /etc/cif/rules/default/csirtg.yml -f port-scanners -d
$ cif --itype ipv4
$ cif-tokens
$ sudo service csirtg-smrt start
```