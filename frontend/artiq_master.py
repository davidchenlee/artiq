#!/usr/bin/env python3

import asyncio
import argparse
import atexit

from artiq.management.pc_rpc import Server
from artiq.management.sync_struct import Publisher
from artiq.management.db import FlatFileDB, SimpleHistory
from artiq.management.scheduler import Scheduler


def _get_args():
    parser = argparse.ArgumentParser(description="ARTIQ master")
    parser.add_argument(
        "--bind", default="::1",
        help="hostname or IP address to bind to")
    parser.add_argument(
        "--port-notify", default=8887, type=int,
        help="TCP port to listen to for notifications")
    parser.add_argument(
        "--port-control", default=8888, type=int,
        help="TCP port to listen to for control")
    return parser.parse_args()


def main():
    args = _get_args()

    ddb = FlatFileDB("ddb.pyon")
    pdb = FlatFileDB("pdb.pyon")
    simplephist = SimpleHistory(30)
    pdb.hooks.append(simplephist)

    loop = asyncio.get_event_loop()
    atexit.register(lambda: loop.close())

    scheduler = Scheduler({
        "req_device": ddb.request,
        "req_parameter": pdb.request,
        "set_parameter": pdb.set
    })
    loop.run_until_complete(scheduler.start())
    atexit.register(lambda: loop.run_until_complete(scheduler.stop()))

    server_control = Server({
        "master_schedule": scheduler,
        "master_ddb": ddb,
        "master_pdb": pdb
    })
    loop.run_until_complete(server_control.start(
        args.bind, args.port_control))
    atexit.register(lambda: loop.run_until_complete(server_control.stop()))

    server_notify = Publisher({
        "queue": scheduler.queue,
        "periodic": scheduler.periodic,
        "devices": ddb.data,
        "parameters": pdb.data,
        "parameters_simplehist": simplephist.history
    })
    loop.run_until_complete(server_notify.start(
        args.bind, args.port_notify))
    atexit.register(lambda: loop.run_until_complete(server_notify.stop()))

    loop.run_forever()

if __name__ == "__main__":
    main()
