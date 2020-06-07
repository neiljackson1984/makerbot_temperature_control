
# This is a module that defines a class, HeaterSetpointManager.  An instance of this class shall be suitable for
# passing to the "kaiten.server.Server" object's "add_contract_generator" method .  This means that an 
# instance of HeaterSetpointDriver must be an iterator (i.e. it must have __next__() method) and
# it must have a contract_duration() method that returns a datetime.timedelta object representing the
# period with which we want the server's ContractGeneratorManager to call the __next__ method.

# to cause the Server object to load this HeaterSetpointManager, pass the following to the Server.debug() method
# some statement to load this heater_setpoint_manager module, then:
# "self.add_contract_generator(heater_setpoint_manager.HeaterSetpointManager(self))"

import datetime
import sys
import os
import time


class HeaterSetpointManager(object):
     
    def __init__(self, server):
        self._server = server

    def contract_duration():
        return datetime.timedelta(seconds=3)
    
    def __next__(self):
        with open("/home/usb_storage/poc.log", "a") as logFile:
            logFile.write((datetime.datetime.now()) + "\n")

 
if __name__ == '__main__':
    #we get here iff. this script is called directly (rather than imported as a module)
    # we shall send commands to kaiten's debug interface to cause kaiten to first load (or reload) this module
    # and then invoke the Server object's add_contract_generator method with an instance of HeaterSetpointManager as the argument.
    #I am not sure exactly what will happen when to existing class instances when we reload the module in which the class is defined.
    # It might be good, before we reload the module, to delete any existing instances of HeaterSetpointManager that happen to be registered
    # (hopefully there would never be more than one) as a contract generator for the Server.

    # This loading function could easily be a separate script.  We only include it here
    # so that only the one file (this python script) needs to be uploaded to the makerbot,
    # for convenience.


    print("heater_setpoint_manager is running as a script.")
    
    import time
    import datetime

    print(str(datetime.datetime.now()) + " " + "atttempting to load heater_setpoint_manager...")
    print('Importing Kaiten')
    import kaiten.address
    print('checkpoint 1')
    import kaiten.constants
    print('checkpoint 2')
    import kaiten.jsonrpc
    print('checkpoint 3')

    responseHasBeenHandled = False
    def _handle_response(response=None, exc=None):
        global responseHasBeenHandled
        responseHasBeenHandled = True
        print("hooray, we're handling a response")
        if exc:
            print(str(exc))
        elif 'result' in response:
            for line in response['result']:
                print(str(line))
        elif 'error' in response:
            print('ERROR: '+ascii(response['error']))
        else:
            print('INVALID RESPONSE')

    def jsonRpcConstructorCallback(x):
        print(str(datetime.datetime.now()) + " " + "jsonRpcConstructorCallback was called with " + str(x))
        listifiedX = []
        for item in x:
            print(str(datetime.datetime.now()) + " " + "x yielded " + "|" + repr(item) + "|")
            listifiedX.append(item)
        print(str(datetime.datetime.now()) + " " + "listifiedX: " + repr(listifiedX))
        # even though lisitifiedX is an empty list, it is necessary to attempt to iterate x (e.g. bvy calling list(x))
        # in order to get the jsonrpc object to call the callback for a request.
        # for item in x: 
        #     print(str(datetime.datetime.now()) + " " + "|" + str(item) + "|")


    print(str(datetime.datetime.now()) + " " + "creating JsonRpc object...")
    jsonrpc = kaiten.jsonrpc.JsonRpc(
        connection=kaiten.address.Address.address_factory(kaiten.constants.pipe).connect(), 
        callback=jsonRpcConstructorCallback
    )
    
    print(str(datetime.datetime.now()) + " " + "issuing JsonRpc request...")
    request = jsonrpc.request(method="debug",params={'expr': "5+14"},result_callback=_handle_response)

    print(str(datetime.datetime.now()) + " " + "iterating the request ...")
    listifiedRequest = []
    for item in request:
        print(str(datetime.datetime.now()) + " " + "request yielded " + "|" + repr(item) + "|" + " " + ("responseHasBeenHandled" if responseHasBeenHandled else ""))
        listifiedRequest.append(item)
    print(str(datetime.datetime.now()) + " " + "listifiedRequest: " + repr(listifiedRequest))

    print(str(datetime.datetime.now()) + " " + "invoking jsonrpc.run() ...")
    jsonrpcRun = jsonrpc.run()

    print(str(datetime.datetime.now()) + " " + "iterating jsonrpcRun ...")
    for item in jsonrpcRun:
        print(str(datetime.datetime.now()) + " " + "jsonrpcRun yielded " + "|" + repr(item) + "|" + " " + ("responseHasBeenHandled" if responseHasBeenHandled else ""))
        if responseHasBeenHandled: break
        time.sleep(0.5)
        


    exit
