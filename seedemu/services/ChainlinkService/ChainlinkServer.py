from seedemu import *
from seedemu.core.enums import NetworkType
from seedemu.services.ChainlinkService import ChainlinkInitializerServer
from seedemu.services.ChainlinkService.ChainlinkTemplates import *
import re

class ChainlinkServer(Server):
    """
    @brief The Chainlink virtual node server.
    """
    __node: Node
    __emulator: Emulator
    __rpc_url: str
    __rpc_vnode_name: str = None
    __username: str = "seed@example.com"
    __password: str = "blockchainemulator"
    __init_node_name: str = None
    __init_node_url: str
    __flask_server_port: int = 5000
    __faucet_node_url: str
    __faucet_vnode_name: str = None
    __faucet_port: int
    __chain_id: int = 1337
    __rpc_ws_port: int = 8546
    __rpc_port: int = 8545    
    
    def __init__(self):
        """
        @brief ChainlinkServer Constructor.
        """
        super().__init__()
        self._base_system = BaseSystem.SEEDEMU_CHAINLINK
        
    def configure(self, node: Node, emulator: Emulator):
        """
        @brief Configure the node.
        """
        self.__node = node
        self.__emulator = emulator

    def install(self, node: Node, faucet_vnode_name: str, faucet_port: int, chainlink_init_server: str):
        """
        @brief Install the service.
        """
        self.__faucet_vnode_name = faucet_vnode_name
        self.__faucet_port = faucet_port
        # Get the ethereum node details
        eth_node = self.__emulator.getServerByVirtualNodeName(self.__rpc_vnode_name)
        # Dynamically set the chain id and rpc port
        self.__chain_id = eth_node.getChainId()
        self.__rpc_port = eth_node.getGethHttpPort()
        self.__rpc_ws_port = eth_node.getGethWsPort()
        
        if chainlink_init_server != "":
            self.__init_node_name = chainlink_init_server
        else:
            raise Exception('Chainlink init server not set')
        
        self.__installSoftware()
        
        if self.__rpc_vnode_name is not None:
            self.__rpc_url = self.__getIPbyEthNodeName(self.__rpc_vnode_name)
        
        if self.__rpc_url is None:
            raise Exception('RPC address not set')
        
        if self.__init_node_name is not None:
            self.__init_node_url = self.__getIPbyEthNodeName(self.__init_node_name)
            
        if self.__init_node_url is None:
            raise Exception('Init node url address not set')
        
        if self.__faucet_vnode_name is not None:
            self.__faucet_node_url = self.__getIPbyEthNodeName(self.__faucet_vnode_name)
            
        if self.__faucet_node_url is None:
            raise Exception('Faucet URL not set')
        
        self.__setConfigurationFiles()
        self.__chainlinkStartCommands()
        self.__node.setFile('/chainlink/send_fund_request.sh', ChainlinkFileTemplate['send_get_eth_request'].format(faucet_server_url=self.__faucet_node_url, faucet_server_port=self.__faucet_port, rpc_url=self.__rpc_url, rpc_port=self.__rpc_port))
        self.__node.appendStartCommand('bash /chainlink/send_fund_request.sh')
        self.__node.setFile('/chainlink/check_init_node.sh', ChainlinkFileTemplate['check_init_node'].format(init_node_url=self.__init_node_url))
        self.__node.appendStartCommand('bash /chainlink/check_init_node.sh')
        self.__deploy_oracle_contract()
        self.__node.setFile('/chainlink/send_flask_request.sh', ChainlinkFileTemplate['send_flask_request'].format(init_node_url=self.__init_node_url, flask_server_port=self.__flask_server_port))
        self.__node.appendStartCommand('bash /chainlink/send_flask_request.sh')
        self.__node.setFile('/chainlink/create_chainlink_jobs.sh', ChainlinkFileTemplate['create_jobs'])
        self.__node.appendStartCommand('bash /chainlink/create_chainlink_jobs.sh')
        self.__node.appendStartCommand('tail -f /chainlink/chainlink_logs.txt')
        
    def __installSoftware(self):
        """
        @brief Install the software.
        """
        software_list = ['ipcalc', 'jq', 'iproute2', 'sed', 'postgresql', 'postgresql-contrib', 'curl', 'python3', 'python3-pip']
        for software in software_list:
            self.__node.addSoftware(software)
        self.__node.addBuildCommand('pip3 install web3==5.31.1')
            
    def __setConfigurationFiles(self):
        """
        @brief Set configuration files.
        """
        config_content = ChainlinkFileTemplate['config'].format(rpc_url=self.__rpc_url, chain_id=self.__chain_id, rpc_ws_port=self.__rpc_ws_port, rpc_port=self.__rpc_port)
        self.__node.setFile('/chainlink/config.toml', config_content)
        self.__node.setFile('/chainlink/db_secret.toml', ChainlinkFileTemplate['secrets'])
        self.__node.setFile('/chainlink/password.txt', ChainlinkFileTemplate['api'].format(username=self.__username, password=self.__password))
        self.__node.setFile('/chainlink/jobs/getUint256.toml', ChainlinkJobsTemplate['getUint256'])
        self.__node.setFile('/chainlink/jobs/getBool.toml', ChainlinkJobsTemplate['getBool'])
        
    def __chainlinkStartCommands(self):
        """
        @brief Add start commands.
        """        
        start_commands = """
service postgresql restart
su - postgres -c "psql -c \\"ALTER USER postgres WITH PASSWORD 'mysecretpassword';\\""
nohup chainlink node -config /chainlink/config.toml -secrets /chainlink/db_secret.toml start -api /chainlink/password.txt > /chainlink/chainlink_logs.txt 2>&1 &
"""
        self.__node.appendStartCommand(start_commands)
    
    def __deploy_oracle_contract(self):
        """
        @brief Deploy the oracle contract.
        """
        self.__node.setFile('/contracts/deploy_oracle_contract.py', OracleContractDeploymentTemplate['oracle_contract_deploy'].format(rpc_url = self.__rpc_url, rpc_port = self.__rpc_port, init_node_url=self.__init_node_url, chain_id=self.__chain_id, faucet_url=self.__faucet_node_url, faucet_port=self.__faucet_port))
        self.__node.setFile('/contracts/oracle_contract.abi', OracleContractDeploymentTemplate['oracle_contract_abi'])
        self.__node.setFile('/contracts/oracle_contract.bin', OracleContractDeploymentTemplate['oracle_contract_bin'])
        self.__node.appendStartCommand(f'python3 ./contracts/deploy_oracle_contract.py')
                
    def setRpcByUrl(self, address: str):
        """
        @brief Set the ethereum RPC address.

        @param address The RPC address or hostname for the chainlink node
        """
        self.__rpc_url = address
        return self
        
    def setLinkedEthNode(self, name:str):        
        """
        @brief Set the ethereum RPC address.

        @param vnode The name of the ethereum node
        """
        self.__rpc_vnode_name = name
        return self
    
    def setUsernameAndPassword(self, username: str, password: str):
        """
        Set the username and password for the Chainlink node API after validating them.

        @param username: The username for the Chainlink node API.
        @param password: The password for the Chainlink node API.
        """
        if not self.__validate_username(username):
            raise ValueError("The username must be a valid email address.")
        if not self.__validate_password(password):
            raise ValueError("The password must be between 16 and 50 characters in length.")

        self.__username = username
        self.__password = password
        return self
        
    def __validate_username(self, username: str) -> bool:
        """
        Check if the username is a valid email address.
        """
        pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
        return re.fullmatch(pattern, username) is not None
    
    def __validate_password(self, password: str) -> bool:
        """
        Check if the password length is between 16 and 50 characters.
        """
        return 16 <= len(password) <= 50
        
    def __getIPbyEthNodeName(self, vnode:str):
        """
        @brief Get the IP address of the ethereum node.
        
        @param vnode The name of the ethereum node
        """
        node = self.__emulator.getBindingFor(vnode)
        address: str = None
        ifaces = node.getInterfaces()
        assert len(ifaces) > 0, 'Node {} has no IP address.'.format(node.getName())
        for iface in ifaces:
            net = iface.getNet()
            if net.getType() == NetworkType.Local:
                address = iface.getAddress()
                break
        return address
          
    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Chainlink server object.\n'
        return out
