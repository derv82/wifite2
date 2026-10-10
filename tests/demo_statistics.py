#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Demonstration of client monitoring and statistics tracking.
"""

import time
from wifite.util.client_monitor import ClientConnection, AttackStatistics

def demo_client_connection():
    """Demonstrate ClientConnection data model."""
    print("\n=== ClientConnection Demo ===")
    
    # Create a client
    client = ClientConnection(
        mac_address="AA:BB:CC:DD:EE:FF",
        ip_address="192.168.100.10",
        hostname="iPhone-12"
    )
    
    print(f"Client: {client}")
    print(f"  MAC: {client.mac_address}")
    print(f"  IP: {client.ip_address}")
    print(f"  Hostname: {client.hostname}")
    print(f"  Connected: {client.is_connected()}")
    print(f"  Credentials submitted: {client.credential_submitted}")
    
    # Simulate credential submission
    time.sleep(1)
    client.credential_submitted = True
    client.credential_valid = True
    
    print(f"\nAfter credential submission:")
    print(f"  Credentials submitted: {client.credential_submitted}")
    print(f"  Credentials valid: {client.credential_valid}")
    print(f"  Connection duration: {client.connection_duration():.2f}s")


def demo_attack_statistics():
    """Demonstrate AttackStatistics tracking."""
    print("\n=== AttackStatistics Demo ===")
    
    stats = AttackStatistics()
    
    print("Initial state:")
    print(f"  Total clients: {stats.total_clients_connected}")
    print(f"  Unique clients: {stats.get_unique_client_count()}")
    print(f"  Credential attempts: {stats.total_credential_attempts}")
    
    # Simulate attack progression
    print("\nSimulating attack...")
    
    # First client connects
    time.sleep(0.5)
    stats.record_client_connect("AA:BB:CC:DD:EE:FF")
    print(f"  Client 1 connected (t={stats.get_time_to_first_client():.2f}s)")
    
    # Second client connects
    time.sleep(0.3)
    stats.record_client_connect("11:22:33:44:55:66")
    print(f"  Client 2 connected")
    
    # First client submits wrong password
    time.sleep(0.5)
    stats.record_credential_attempt(success=False)
    print(f"  Failed credential attempt (t={stats.get_time_to_first_credential():.2f}s)")
    
    # First client submits correct password
    time.sleep(0.2)
    stats.record_credential_attempt(success=True)
    print(f"  Successful credential attempt (t={stats.get_time_to_success():.2f}s)")
    
    # Display final statistics
    print("\nFinal statistics:")
    print(f"  Duration: {stats.get_duration():.2f}s")
    print(f"  Total clients: {stats.total_clients_connected}")
    print(f"  Unique clients: {stats.get_unique_client_count()}")
    print(f"  Currently connected: {stats.currently_connected}")
    print(f"  Credential attempts: {stats.total_credential_attempts}")
    print(f"  Successful: {stats.successful_attempts}")
    print(f"  Failed: {stats.failed_attempts}")
    print(f"  Success rate: {stats.get_success_rate():.1f}%")
    
    # Show dictionary representation
    print("\nStatistics as dictionary:")
    for key, value in stats.to_dict().items():
        if value is not None:
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
    
    # Show string representation
    print("\nString representation:")
    print(stats)


if __name__ == '__main__':
    demo_client_connection()
    demo_attack_statistics()
    print("\n=== Demo Complete ===\n")
