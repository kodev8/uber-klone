def log(string):
    """
    Only print output if this is specified in the configuration
    :param string: string to be printed
    """
    from admin_bp.dashboard import config

    if config.enable_logging:
        print(string)
