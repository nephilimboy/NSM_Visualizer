import json

from kubernetes import client
from kubernetes.client import ApiClient, ApiException
from kubernetes import config
from kubernetes.stream import stream

from http.server import BaseHTTPRequestHandler, HTTPServer, SimpleHTTPRequestHandler
import time


NameSpace = "ns-carleton-services"
# PathToK8sConfigFile = "./admin.conf"
PathToK8sConfigFile = "/etc/kubernetes/admin.conf"
hostName = "167.99.181.37"
serverPort = 9595


class Nic:

    def __init__(self, name, ip, ns_name):
        self.name = name
        self.ip = ip
        self.ns_name = ns_name


class Pod:
    interfaces = []
    def __init__(self, name, workerNode):
        self.name = name
        self.workerNode = workerNode


class MyServer(BaseHTTPRequestHandler):

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', '*')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        return super(MyServer, self).end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(json.dumps(makeNetworkGraph( readNetworkDataFromK8s() )), "utf8"))



def readNetworkDataFromK8s():
    podList = []
    config.load_kube_config(config_file=PathToK8sConfigFile)
    v1 = client.CoreV1Api()


    try:
        podJsonResponse = v1.list_namespaced_pod(NameSpace)

    except ApiException as e:
        if e.status != 404:
            print(f"Unknown error: {e}")
            exit(1)

    for podItemStr in podJsonResponse.items:
        ## Making pod obg with pod's name and deployed worker node's name
        podTmp = Pod(podItemStr.metadata.name, podItemStr.spec.node_name)

        ## Get the first container in the pod to Execute command to get the list of interface with format NicName:IP separated with "\n"
        exec_command = [
            '/bin/sh',
            '-c',
            'ip --oneline addr show | awk \'$3 == "inet" && $2 != "lo" { print $2 ":" $4 }\'']

        listOfInterfacesStr = stream(v1.connect_get_namespaced_pod_exec,
                                     podTmp.name,
                                     ## Name of the first container in the Pod
                                     NameSpace,
                                     container=podItemStr.status.container_statuses[0].name,
                                     command=exec_command,
                                     stderr=True, stdin=False,
                                     stdout=True, tty=False)


        podTmp.interfaces = []
        ## NicName:IP
        for interfaceStr in listOfInterfacesStr.split("\n"):
            ## Dont show the eth0 interface since its from K8s no NSM
            if interfaceStr != "" and interfaceStr.split(":")[0] != "eth0":
                podTmp.interfaces.append(Nic(interfaceStr.split(":")[0], interfaceStr.split(":")[1], ""))



        ## Find Network Service's (NS) name associated with NIC
        ## Read YAML configuration of each container in Pod to get the NS name
        for containerConfig in podItemStr.spec.containers:
            ## Loop through the Env defined in the YAML file

            ###### For NSE containers ######
            ## Find NS name first before finding the NIC
            if containerConfig.env != None:
                nsNameTemp = "";
                for environmentVar in containerConfig.env:
                    if environmentVar.name == "NSM_SERVICE_NAMES":
                        nsNameTemp = environmentVar.value
                        break

                if nsNameTemp != "":
                    for environmentVar in containerConfig.env:
                        ##'name': 'NSM_CIDR_PREFIX',
                        ##'value': '172.16.1.100/31',
                        ## Identifying based on the IP subrange
                        if environmentVar.name == "NSM_CIDR_PREFIX":
                            ## Loop through NICs to find the same IP range
                            for nic in podTmp.interfaces:
                                if nic.ip.split(".")[0] == environmentVar.value.split(".")[0] and nic.ip.split(".")[1] == \
                                        environmentVar.value.split(".")[1] and nic.ip.split(".")[2] == environmentVar.value.split(".")[2]:
                                    nic.ns_name = nsNameTemp

                ###### For NSC containers ######
                else:
                    for environmentVar in containerConfig.env:
                        ##'name': 'NSM_NETWORK_SERVICES',
                        ##'value': 'kernel://fr1-t-fr2-serv/nsm-1,kernel://fr1-t-fr22-serv/nsm-2',
                        if environmentVar.name == "NSM_NETWORK_SERVICES":
                            if len(environmentVar.value.split(",")) > 1:
                                for nsm_kernel_path in environmentVar.value.split(","):
                                    for nic in podTmp.interfaces:
                                        ## ['kernel:', '', 'fr1-t-fr2-serv', 'nsm-1']
                                        if nic.name == nsm_kernel_path.split("/")[3]:
                                            nic.ns_name = nsm_kernel_path.split("/")[2]
                            else:
                                for nic in podTmp.interfaces:
                                    ## ['kernel:', '', 'fr1-t-fr2-serv', 'nsm-1']
                                    if nic.name == environmentVar.value.split("/")[3]:
                                        nic.ns_name = environmentVar.value.split("/")[2]

        # print("-----------")
        # print(podTmp.__dict__)
        # for nic in podTmp.interfaces:
        #     print(nic.__dict__)
        # print("-----------")
        podList.append(podTmp)
    return podList

def makeNetworkGraph(podList):
    time.sleep(1)
    ## History of all already parsed ns to avoid more loops!
    nsLookUpHistory = []
    nodes = []
    edges = []
    for podObj in podList:
        nodes.append({
            'id': podObj.name,
            'label': podObj.name + "\n" + podObj.workerNode
        })
    ## Need to get each unique ID so we can have multiple edge from same source to the same destination
    edgeIdCounter = 0
    for srcPodObj in podList:
        for srcInterface in srcPodObj.interfaces:
            ## History of all already parsed ns to avoid more loops!
            if srcInterface.ns_name in nsLookUpHistory:
                continue
            for destPodObj in podList:
                ## Dont want to compare it with itself!
                if srcPodObj.name == destPodObj.name:
                    continue
                for destInterface in destPodObj.interfaces:
                    if srcInterface.ns_name == destInterface.ns_name:
                        edgeIdCounter += 1
                        nsLookUpHistory.append(srcInterface.ns_name)
                        edges.append({
                            'id': 'edge'+str(edgeIdCounter),
                            'source': srcPodObj.name,
                            'target': destPodObj.name,
                            'label': srcInterface.name  + " <-> " + destInterface.name + "\n" + srcInterface.ip + "<-> " + destInterface.ip
                        })


    data = {
        'nodes': nodes,
        'edges': edges
    }
    print(data)
    return data


if __name__ == "__main__":

    webServer = HTTPServer((hostName, serverPort), MyServer)
    print("Server started http://%s:%s" % (hostName, serverPort))
    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    webServer.server_close()
    print("Server stopped.")





