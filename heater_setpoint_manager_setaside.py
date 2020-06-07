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

    print("atttempting to load heater_setpoint_manager...")
    
    # print("importing repl...")
    # pathOfReplScript="/usr/scripts/repl.py"

    # if os.path.dirname(pathOfReplScript) not in sys.path:
    #     sys.path.append(os.path.dirname(pathOfReplScript))
    # import repl

    # print("creating repl client...")
    # client = repl.Client()

    # def _handle_response(self, response=None, exc=None):
    #     print("hooray, we received a response: " + str(response))
    #     if exc:
    #         print(str(exc))
    #     elif 'result' in response:
    #         # debug() returns a list of strings to print
    #         for line in response['result']:
    #             print(str(line))
    #     elif 'error' in response:
    #         print('ERROR: '+ ascii(response['error']))
    #     else:
    #         print('INVALID RESPONSE')

    # def _send(generator):
    #     print("send_ was called with " + str(generator))
    #     for item in generator: print(item)

    # # print("sending command to repl client...")
    # # client.handle_cmd(cmd="5+5",callback=_handle_response,debug=True)
    
    # # print("running repl client...")
    # # client.run()


    # import kaiten.address
    # import kaiten.constants
    # import kaiten.jsonrpc

    # address = kaiten.address.Address.address_factory(kaiten.constants.pipe)
    # connection = address.connect()
    # _jsonrpc = kaiten.jsonrpc.JsonRpc(connection, _send)
    # # kaiten.jsonrpc.install(self._jsonrpc, self)


    # request = _jsonrpc.request(method="debug", params={'expr':"5+5"}, result_callback=_handle_response)
    # for item in request: print(str(item))
    import code
    import inspect
    import logging
    import signal
    import threading
    import traceback

    import kaiten.address
    import kaiten.constants
    import kaiten.decorator
    import kaiten.jsonrpc
    import kaiten.server

    from kaiten.scheduler import IOPollGenerator, ContractGeneratorManager
    from kaiten.generators import IOGenerator
    from kaiten.server import GeneratorQueue, ThreadGeneratorQueue
    from kaiten.decorator import FunctionAttributes as fn_attrs

    class CancelHandle(object):
        """
        Each request gets a handle that can be used to cancel it.  All
        cancelling means is no longer waiting for the request to complete
        and returning the user to the repl prompt.
        """
        def __init__(self): self.cancelled = False
        def cancel(self): self.cancelled = True


    class Client(object):
        def __init__(self):
            logging.basicConfig(filename='/home/usbe_storage/repl.log', level=logging.INFO)
            self._log = logging.getLogger('repl')
            self._iopoll = IOPollGenerator(self._handle_io_error)
            self._generator_manager = ContractGeneratorManager(self._iopoll)
            self._tqueue = ThreadGeneratorQueue()
            self._iopoll.register(self._tqueue)
            self._install_signal_handlers()
            self._methods = Methods(self._request)
            self._callback = None
            # self._process = None
            self._cancel_handle = None
            self._connected = False
            self._repl = Repl(self)
            self._repl.start()

        def _install_signal_handlers(self):
            signal.signal(signal.SIGINT, self._handle_sigint)

        def _handle_sigint(self, signum, frame):
            self._tqueue.push_back(self._cancel())

        def connect(self):
            address = kaiten.address.Address.address_factory(kaiten.constants.pipe)
            connection = address.connect()
            self._queue = GeneratorQueue(self._iopoll, connection, False, True)
            self._jsonrpc = kaiten.jsonrpc.JsonRpc(connection, self._send)
            generator = IOGenerator(self._jsonrpc.run(), connection, True, False)
            self._iopoll.register(generator)
            # kaiten.jsonrpc.install(self._jsonrpc, self)
            self._connected = True

        def _send(self, generator):
            self._queue.push_back(generator)

        def run(self):
            self._generator_manager.run()

        def stop(self):
            self._generator_manager.stop()
            def wakeup(): yield
            self._tqueue.push_back(wakeup())

        def handle_cmd(self, cmd, callback, debug=True):
            self._tqueue.push_back(self._handle_cmd(cmd, callback, debug))

        def _handle_cmd(self, cmd, callback, debug=True):
            self._callback = callback
            try:
                res = self._methods.debug(cmd)   
            except Exception as e:
                callback(exc=e)
                self._callback = None
                self._log.error("Exception running '%s'", cmd, exc_info=True)
            else:
                if res is not Methods._Sentinel:
                    callback({'result': res})
                    self._callback = None

        def _cancel(self):
            if False: yield
            if self._cancel_handle:
                self._cancel_handle.cancel()
                self._cancel_handle = None
            if self._process:
                started = 'id' in self._process
                self._process['callback'](exc=ProcessCancelledError(started))
                self._process = None
            elif self._callback:
                self._callback(exc=MethodCancelledError())
                self._callback = None

        def _request(self, method, params, process=False):
            if not self._connected:
                self.connect()
            self._log.info('Invoking request %s', method)
            self._cancel_handle = cancel_handle = CancelHandle()
            if process:
                self._process = {'done_ids': {}, 'callback': self._callback}
                self._callback = None
                def callback(response):
                    if not cancel_handle.cancelled:
                        self._process_started(response)
                        self._cancel_handle = None
            else:
                def callback(response):
                    if not cancel_handle.cancelled:
                        self._callback(response)
                        self._callback = None
                        self._cancel_handle = None
            request = self._jsonrpc.request(method, params, callback)
            self._send(request)

        def _handle_io_error(self, io_generator, exc):
            self._log.error('IO Error: %s', exc)

        def _process_started(self, response):
            info = response.get('result')
            process_started = (isinstance(info, dict) and
                            all(x in info for x in ['id', 'step']))
            callback = self._process['callback']
            if not process_started:
                callback(response)
                self._process = None
            elif info['id'] in self._process['done_ids']:
                # The process finished before the response occured
                # This logic could be so much simpler if we could
                # guarantee that this would never happen.
                callback({'result': self._process['done_ids'][info['id']]})
                self._process = None
            else:
                del self._process['done_ids']
                self._process['id'] = info['id']

        @kaiten.decorator.jsonrpc
        def state_notification(self, info):
            process_info = info['current_process']
            if self._process and process_info and process_info['step'] == 'done':
                # A process has finished and we are
                # waiting for a process to finish...
                if 'id' not in self._process:
                    # ...but we don't know if this is the process
                    # we are waiing for, so cache the result.
                    self._process['done_ids'][process_info['id']] = process_info
                elif self._process['id'] == process_info['id']:
                    # .. and this is the process we are waiting for
                    callback = self._process['callback']
                    callback({'result': process_info})
                    self._process = None

    

    class Methods(object):
        _Sentinel = object()

        def __init__(self, request):
            self._methods = {}
            self._request = request
            self._parse_kaiten()
            # Used to check what methods are processes
            self._ref_process = kaiten.decorator.register_process(lambda:None)

        def help(self, methodname=None, msg=None):
            # Raise an appropriate UsageError
            if not methodname:
                methods = sorted(self._methods.keys())
                raise UsageError('\n'.join(methods))
            elif methodname not in self._methods:
                raise AttributeError('Unknown method '+methodname)
            else:
                method = self._get_method(methodname)
                proto = self._get_proto(methodname, method['params'])
                usage = 'Usage:\n%s\n\n%s'% (proto, method['doc'])
                raise UsageError(usage, msg)

        def __getattr__(self, attr):
            if attr not in self._methods:
                raise AttributeError('Unknown method '+attr)
            method = self._get_method(attr)
            def invoke(*args, **kwargs):
                # Convert args+kwargs into just kwargs, display a usage
                # message if this is not possible.
                # TODO: actually display usage instead of raising TypeErrors
                params = {}
                if len(args) > len(method['params']):
                    self.help(attr, 'Too many arguments')
                for arg, param in zip(args, method['params']):
                    params[param[0]] = arg
                leftovers = method['params'][len(args):]
                for name, param in leftovers:
                    if name in kwargs:
                        params[name] = kwargs[name]
                        del kwargs[name]
                    elif param.default is inspect.Parameter.empty:
                        self.help(attr, 'Missing required argument '+name)
                for name in kwargs:
                    self.help(attr, 'Unknown keyword argument '+name)
                if method['machine']:
                    params = {'machine_func': attr, 'params': params}
                    func = method['machine']
                else:
                    func = attr
                self._request(func, params, method['is_process'])
                return self._Sentinel
            return invoke

        def _is_process(self, method):
            # TODO: inspect probably provides a better way to do this.
            while method:
                if method.__code__ is self._ref_process.__code__:
                    return True
                method = getattr(method, '__wrapped__', None)
            return False

        def _get_method(self, attr):
            method = self._methods[attr]
            if isinstance(method, dict):
                return method
            sig = inspect.signature(method)
            doc = inspect.getdoc(method)
            has_pass_client = getattr(method, fn_attrs.pass_client, False)
            has_pass_callback = getattr(method, fn_attrs.pass_callback, False)
            if getattr(method, fn_attrs.jsonrpc, False):
                machine = None
                is_process = self._is_process(method)
            elif inspect.isgeneratorfunction(method):
                machine = 'machine_action_command'
                is_process = True
            else:
                machine = 'machine_query_command'
                is_process = False
            self._methods[attr] = method = {
                'doc': doc,
                'machine': machine,
                'is_process': is_process,
            }

            # Get a list of real parameters (skip the first argument and
            # any internal use parameters.
            method['params'] = []
            for name, param in list(sig.parameters.items())[1:]:
                if name == 'client' and has_pass_client:
                    continue
                if name == 'callback' and has_pass_callback:
                    continue
                method['params'].append((name, param))

            return method

        def _get_proto(self, name, params):
            return '%s(%s)'%(name, ', '.join(p[0] for p in params))

        def _is_json_method(self, func):
            """
            Returns True if func is a jsonrpc exposed function/method
            at or below the given privelege level
            """
            return ((inspect.isclass(func)
                or inspect.ismethod(func)
                or inspect.isfunction(func))
                and getattr(func, fn_attrs.jsonrpc, False))

        def _parse_object(self, obj):
            """
            Looks at all attributes in an object. If any of those
            objects are JSON-RPC exposed funcs/methods, add them to
            self._methods
            """
            for name, attr in inspect.getmembers(obj):
                # Skip python's builtin members
                if name.startswith('__'):
                    continue
                # If an object is a class, we need to inspect it
                # and find all json exposed funcs
                if inspect.isclass(attr):
                    self._parse_object(attr)
                # We need to see if this object is a json exposed
                # object.  NB: Even classes can be json exposed
                if self._is_json_method(attr):
                    self._methods[name] = attr

        def _parse_kaiten(self):
            """
            Find all of kaiten's jsonrpc methods.  Also expose pymachine methods
            as top level, since thats what host driver does.
            """
            mod = __import__('kaiten')
            for name, obj in inspect.getmembers(mod):
                # Skip python's builtin members
                if name.startswith('__'):
                    continue
                self._parse_object(obj)
            pymach_override = {
                'home': 'pymach_home',
            }
            try:
                import libmachine.pymachine
            except ImportError:
                return
            for name, obj in inspect.getmembers(libmachine.pymachine.Machine):
                if name.startswith('_') or name in self._methods:
                    continue
                self._methods[pymach_override.get(name, name)] = obj




    class Repl(threading.Thread):
        def __init__(self, client):
            self._client = client
            self._event = threading.Event()
            self._debug = False
            super().__init__()

        def _handle_response(self, response=None, exc=None):
            if exc:
                print(str(exc))
            elif 'result' in response:
                for line in response['result']:
                    print(str(line))
            elif 'error' in response:
                print('ERROR: '+ascii(response['error']))
            else:
                print('INVALID RESPONSE')
            self._event.set()

        def run(self):
            print('Welcome to the onboard repl')
            while True:
                self._client.handle_cmd("5+5", self._handle_response, self._debug)
                self._event.wait()
                self._event.clear()
                time.sleep(10)
            self._client.stop()

    client = Client()
    client.run()

    print("waiting for response from kaiten")
    time.sleep(100)
    
    exit

