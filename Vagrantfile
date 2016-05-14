#e -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"
VAGRANTFILE_LOCAL = 'Vagrantfile.local'

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = 'ubuntu/trusty64'

  config.vm.network :forwarded_port, guest: 5000, host: 5000
  config.vm.provider :virtualbox do |vb|
    vb.customize ["modifyvm", :id, "--cpus", "2", "--ioapic", "on", "--memory", "512" ]
  end

  config.vm.provision "shell", inline: <<-END
    echo GH_TOKEN=#{ENV['GH_TOKEN']} >> /home/vagrant/.profile
  END

  #config.vm.provision "ansible" do |ansible|
    #ansible.playbook = "deployment/ubuntu14/vagrant.yml"
    #ansible.extra_vars = { development: 'true' }
    #ansible.verbose = 'vvv'
  #end

  if File.file?(VAGRANTFILE_LOCAL)
    external = File.read VAGRANTFILE_LOCAL
    eval external
  end
end
