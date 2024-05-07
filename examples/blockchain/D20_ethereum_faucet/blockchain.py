#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import sys
from examples.internet.B00_mini_internet import mini_internet


emu = Emulator()

# Run and load the pre-built component
mini_internet.run(dumpfile='./base-internet.bin')
emu.load('./base-internet.bin')

#This is another way to generate the base internet
#emu = Makers.makeEmulatorBaseWith10StubASAndHosts(1)

# Create the Ethereum layer
# saveState=True: will set the blockchain folder using `volumes`, 
# so the blockchain data will be preserved when containers are deleted.
eth = EthereumService(saveState = False, override=True)

# Create a POA Blockchain layer, which is a sub-layer of Ethereum layer
# Need to specify chainName and consensus when create Blockchain layer.
blockchain1 = eth.createBlockchain(chainName="POA", consensus=ConsensusMechanism.POA)

# Create blockchain1 nodes (POA Etheruem) (nodes in this layer are virtual)
e1 = blockchain1.createNode("poa-eth1").enableGethHttp().setDisplayName('Ethereum-POA-1')
e2 = blockchain1.createNode("poa-eth2").enableGethHttp().setDisplayName('Ethereum-POA-2')
e3 = blockchain1.createNode("poa-eth3").enableGethHttp().setDisplayName('Ethereum-POA-3')
e4 = blockchain1.createNode("poa-eth4").enableGethHttp().setDisplayName('Ethereum-POA-4')
e5 = blockchain1.createNode("poa-eth5").enableGethHttp().setDisplayName('Ethereum-POA-5')
e6 = blockchain1.createNode("poa-eth6").enableGethHttp().setDisplayName('Ethereum-POA-6')
e7 = blockchain1.createNode("poa-eth7").enableGethHttp().setDisplayName('Ethereum-POA-7')
e8 = blockchain1.createNode("poa-eth8").enableGethHttp().setDisplayName('Ethereum-POA-8')

# Set bootnodes on e1 and e5. The other nodes can use these bootnodes to find peers.
# Start mining on e1,e2, e5, and e6
# To start mine(seal) in POA consensus, the account should be unlocked first. 
e1.setBootNode(True).unlockAccounts().startMiner()
e2.unlockAccounts().startMiner()
e5.setBootNode(True).unlockAccounts().startMiner()
e6.unlockAccounts().startMiner()

# Set port forwarding on eth3
emu.getVirtualNode('poa-eth3').addPortForwarding(8545, 8540)

# Binding virtual nodes to physical nodes
emu.addBinding(Binding('poa-eth1', filter = Filter(asn = 150, nodeName='host_0')))
emu.addBinding(Binding('poa-eth2', filter = Filter(asn = 151, nodeName='host_0')))
emu.addBinding(Binding('poa-eth3', filter = Filter(asn = 152, nodeName='host_0')))
emu.addBinding(Binding('poa-eth4', filter = Filter(asn = 153, nodeName='host_0')))
emu.addBinding(Binding('poa-eth5', filter = Filter(asn = 160, nodeName='host_0')))
emu.addBinding(Binding('poa-eth6', filter = Filter(asn = 161, nodeName='host_0')))
emu.addBinding(Binding('poa-eth7', filter = Filter(asn = 162, nodeName='host_0')))
emu.addBinding(Binding('poa-eth8', filter = Filter(asn = 163, nodeName='host_0')))

# Enable http connection on e5 geth
e5.enableGethHttp()

# Faucet Service
blockchain1:Blockchain
# Make sure that eth5 node has enabled geth.
faucet:FaucetServer = blockchain1.createFaucetServer(vnode='faucet', 
                                                     port=80, 
                                                     linked_eth_node='poa-eth5',
                                                     balance=1000)


faucet.fund('0x72943017a1fa5f255fc0f06625aec22319fcd5b3', 2)
faucet.fund('0x5449ba5c5f185e9694146d60cfe72681e2158499', 5)

emu.addBinding(Binding('faucet', filter=Filter(asn=154, nodeName='host_0')))

faucetUserService = FaucetUserService()
faucetUserService.install('faucetUser')
faucetUserService.setFaucetServerInfo(vnode = 'faucet', port=80)
emu.addBinding(Binding('faucetUser', filter=Filter(asn=164, nodeName='host_0')))


# Add the layer and save the component to a file
emu.addLayer(eth)
emu.addLayer(faucetUserService)

emu.render()

if len(sys.argv) == 1:
    platform = "amd"
else:
    platform = sys.argv[1]

platform_mapping = {
    "amd": Platform.AMD64,
    "arm": Platform.ARM64
}

docker = Docker(etherViewEnabled=True, platform=platform_mapping[platform])
emu.compile(docker, './output', override=True)

