#e -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"
VAGRANTFILE_LOCAL = 'Vagrantfile.local'

sdist=ENV['CIF_ANSIBLE_SDIST']
es=ENV['CIF_ANSIBLE_ES']
hunter_threads=ENV['CIF_HUNTER_THREADS']
geo_fqdn=ENV['CIF_GATHERER_GEO_FQDN']
csirtg_token=ENV['CSIRTG_TOKEN']

unless File.directory?('deploymentkit')
    puts "Please unzip the latest release of the deploymentkit before continuing..."
    puts ""
    puts "https://github.com/csirtgadgets/bearded-avenger-deploymentkit/wiki"
    puts ""
    exit
end

$script = <<SCRIPT
export CIF_ANSIBLE_SDIST=#{sdist}
export CIF_ANSIBLE_ES=#{es}
export CIF_HUNTER_THREADS=#{hunter_threads}
export CIF_GATHERER_GEO_FQDN=#{geo_fqdn}
export CIF_BOOTSTRAP_TEST=1
export CSIRTG_TOKEN=#{csirtg_token}

echo "export CSIRTG_TOKEN='${CSIRTG_TOKEN}'" >> /home/ubuntu/.profile

cd /vagrant/deploymentkit
bash easybutton.sh
SCRIPT

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.provision "shell", inline: $script
  config.vm.box = 'ubuntu/xenial64'

  config.vm.network :forwarded_port, guest: 443, host: 8443
  
  config.vm.provider :virtualbox do |vb|
    vb.customize ["modifyvm", :id, "--cpus", "2", "--ioapic", "on", "--memory", "1024" ]
  end

  if File.file?(VAGRANTFILE_LOCAL)
    external = File.read VAGRANTFILE_LOCAL
    eval external
  end
end
