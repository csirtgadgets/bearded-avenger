#e -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"
VAGRANTFILE_LOCAL = 'Vagrantfile.local'

sdist=ENV['CIF_ANSIBLE_SDIST']
es=ENV['CIF_ANSIBLE_ES']
test=ENV['CIF_BOOTSTRAP_TEST']

$script = <<SCRIPT
export CIF_ANSIBLE_SDIST=#{sdist}
export CIF_ANSIBLE_ES=#{es}
export CIF_BOOTSTRAP_TEST=#{test}

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
