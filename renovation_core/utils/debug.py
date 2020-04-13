def wait_for_attach(host="localhost", port=5678):
  import ptvsd
  # Allow other computers to attach to ptvsd at this IP address and port.
  ptvsd.enable_attach(address=(host, port), redirect_output=True)
  # Pause the program until a remote debugger is attached
  print("\n\t[ptvsd] Waiting for debugger to attach\n")
  ptvsd.wait_for_attach()
