#!/usr/bin/env python3
"""
DNS Failure Analysis Script
Analyzes DNS failure CSV data and provides distribution statistics
for domains, devices, DNS servers, and sites.
"""

import csv
import re
import argparse
from collections import Counter, defaultdict
from pathlib import Path
import sys

class DNSFailureAnalyzer:
    def __init__(self, csv_file_path):
        self.csv_file_path = Path(csv_file_path)
        self.data = []
        self.domains = Counter()
        self.devices = Counter()
        self.dns_servers = Counter()
        self.sites = Counter()
        self.device_manufacturers = Counter()
        self.device_os = Counter()
        self.vlans = Counter()
        self.hourly_distribution = Counter()
        
    def load_data(self):
        """Load and parse the CSV data"""
        print(f"Loading data from {self.csv_file_path}...")
        
        try:
            with open(self.csv_file_path, 'r', encoding='utf-8') as file:
                # Use a more robust CSV parsing approach
                reader = csv.reader(file)
                headers = next(reader)  # Get headers
                
                # Map field indices
                field_map = {header.strip(): i for i, header in enumerate(headers)}
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Safely get field values
                        dns_text = row[field_map.get('Client Event Text', 6)] if len(row) > 6 else ''
                        timestamp = row[field_map.get('Client Event Event Timestamp Local Time', 2)] if len(row) > 2 else ''
                        site = row[field_map.get('Site Site Name', 3)] if len(row) > 3 else ''
                        device_hostname = row[field_map.get('Client Device Info Client Hostname', 7)] if len(row) > 7 else ''
                        ssid = row[field_map.get('Wlan Ssid', 8)] if len(row) > 8 else ''
                        client_mac = row[field_map.get('Client Event Mac Address', 9)] if len(row) > 9 else ''
                        device_family = row[field_map.get('Client Device Info Client Family', 10)] if len(row) > 10 else ''
                        device_model = row[field_map.get('Client Device Info Client Model', 11)] if len(row) > 11 else ''
                        device_os = row[field_map.get('Client Device Info Client OS', 12)] if len(row) > 12 else ''
                        device_manufacturer = row[field_map.get('Client Device Info Client Manufacture', 13)] if len(row) > 13 else ''
                        
                        # Parse DNS query text to extract domain and servers
                        domain = self._extract_domain(dns_text)
                        source_ip, dest_ip = self._extract_ips(dns_text)
                        vlan = self._extract_vlan(dns_text)
                        
                        # Extract timestamp hour
                        hour = self._extract_hour(timestamp)
                        
                        # Store parsed data
                        parsed_row = {
                            'domain': domain,
                            'source_ip': source_ip,
                            'dns_server': dest_ip,
                            'vlan': vlan,
                            'site': site.strip().strip('"'),
                            'device_hostname': device_hostname.strip().strip('"'),
                            'ssid': ssid.strip().strip('"'),
                            'client_mac': client_mac.strip().strip('"'),
                            'device_family': device_family.strip().strip('"'),
                            'device_model': device_model.strip().strip('"'),
                            'device_os': device_os.strip().strip('"'),
                            'device_manufacturer': device_manufacturer.strip().strip('"'),
                            'timestamp': timestamp.strip().strip('"'),
                            'hour': hour
                        }
                        
                        self.data.append(parsed_row)
                        
                        # Update counters
                        if domain:
                            self.domains[domain] += 1
                        if parsed_row['dns_server']:
                            self.dns_servers[parsed_row['dns_server']] += 1
                        if parsed_row['site']:
                            self.sites[parsed_row['site']] += 1
                        if parsed_row['device_hostname']:
                            self.devices[parsed_row['device_hostname']] += 1
                        if parsed_row['device_manufacturer']:
                            self.device_manufacturers[parsed_row['device_manufacturer']] += 1
                        if parsed_row['device_os']:
                            self.device_os[parsed_row['device_os']] += 1
                        if vlan:
                            self.vlans[vlan] += 1
                        if hour is not None:
                            self.hourly_distribution[hour] += 1
                            
                    except Exception as e:
                        print(f"Error processing row {row_num}: {e}")
                        continue
                        
        except FileNotFoundError:
            print(f"Error: File not found: {self.csv_file_path}")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(1)
            
        print(f"Loaded {len(self.data)} DNS failure records")
    
    def _extract_domain(self, dns_text):
        """Extract domain from DNS query text"""
        # Pattern: 'for "domain.com"' (single quotes around the whole string, double quotes around domain)
        match = re.search(r'for "([^"]*?)"', dns_text)
        return match.group(1) if match else None
    
    def _extract_ips(self, dns_text):
        """Extract source and destination IPs from DNS query text"""
        # Pattern: 'from IP1 to IP2'
        match = re.search(r'from (\d+\.\d+\.\d+\.\d+) to (\d+\.\d+\.\d+\.\d+)', dns_text)
        if match:
            return match.group(1), match.group(2)
        return None, None
    
    def _extract_vlan(self, dns_text):
        """Extract VLAN from DNS query text"""
        # Pattern: 'on vlan 123'
        match = re.search(r'on vlan (\d+)', dns_text)
        return int(match.group(1)) if match else None
    
    def _extract_hour(self, timestamp):
        """Extract hour from timestamp"""
        # Pattern: 'YYYY-MM-DD HH:MM:SS'
        match = re.search(r'\d{4}-\d{2}-\d{2} (\d{2}):', timestamp)
        return int(match.group(1)) if match else None
    
    def print_distribution(self, counter, title, top_n=20):
        """Print distribution statistics"""
        print(f"\n{'='*60}")
        print(f"{title.upper()} DISTRIBUTION")
        print(f"{'='*60}")
        print(f"Total unique {title.lower()}: {len(counter)}")
        print(f"Total failures: {sum(counter.values())}")
        print(f"\nTop {top_n} {title.lower()}:")
        print(f"{'Rank':<5} {'Count':<10} {'Percentage':<12} {title}")
        print('-' * 60)
        
        total = sum(counter.values())
        for i, (item, count) in enumerate(counter.most_common(top_n), 1):
            percentage = (count / total) * 100
            print(f"{i:<5} {count:<10} {percentage:<11.2f}% {item}")
    
    def print_summary_stats(self):
        """Print overall summary statistics"""
        total_failures = len(self.data)
        print(f"\n{'='*60}")
        print("SUMMARY STATISTICS")
        print(f"{'='*60}")
        print(f"Total DNS Failures: {total_failures:,}")
        print(f"Unique Domains: {len(self.domains):,}")
        print(f"Unique Devices: {len(self.devices):,}")
        print(f"Unique DNS Servers: {len(self.dns_servers):,}")
        print(f"Unique Sites: {len(self.sites):,}")
        print(f"Unique VLANs: {len(self.vlans):,}")
        print(f"Unique Device Manufacturers: {len(self.device_manufacturers):,}")
        
        # Microsoft connectivity test analysis
        ms_connectivity_domains = [
            'ipv6.msftconnecttest.com',
            'www.msftconnecttest.com',
            'dns.msftncsi.com'
        ]
        
        ms_failures = sum(self.domains[domain] for domain in ms_connectivity_domains)
        ms_percentage = (ms_failures / total_failures) * 100
        
        print(f"\nMicrosoft Connectivity Tests:")
        print(f"  Failures: {ms_failures:,} ({ms_percentage:.1f}%)")
        print(f"  Real DNS Issues: {total_failures - ms_failures:,} ({100 - ms_percentage:.1f}%)")
    
    def print_hourly_distribution(self):
        """Print hourly distribution of DNS failures"""
        print(f"\n{'='*60}")
        print("HOURLY DISTRIBUTION")
        print(f"{'='*60}")
        print(f"{'Hour':<5} {'Count':<10} {'Percentage':<12} {'Visual'}")
        print('-' * 60)
        
        total = sum(self.hourly_distribution.values())
        max_count = max(self.hourly_distribution.values()) if self.hourly_distribution else 0
        
        for hour in range(24):
            count = self.hourly_distribution.get(hour, 0)
            percentage = (count / total) * 100 if total > 0 else 0
            bar_length = int((count / max_count) * 30) if max_count > 0 else 0
            bar = '█' * bar_length
            print(f"{hour:02d}:00 {count:<10} {percentage:<11.2f}% {bar}")
    
    def analyze(self, top_n=20):
        """Perform complete analysis and print results"""
        self.load_data()
        
        if not self.data:
            print("No data to analyze!")
            return
        
        # Print summary
        self.print_summary_stats()
        
        # Print distributions
        self.print_distribution(self.domains, "Domain", top_n)
        self.print_distribution(self.dns_servers, "DNS Server", top_n)
        self.print_distribution(self.sites, "Site", top_n)
        self.print_distribution(self.devices, "Device", top_n)
        self.print_distribution(self.device_manufacturers, "Device Manufacturer", top_n)
        self.print_distribution(self.device_os, "Device OS", top_n)
        self.print_distribution(self.vlans, "VLAN", top_n)
        
        # Print hourly distribution
        self.print_hourly_distribution()
    
    def export_analysis(self, output_file):
        """Export analysis results to a file"""
        with open(output_file, 'w') as f:
            # Redirect print output to file
            original_stdout = sys.stdout
            sys.stdout = f
            
            self.print_summary_stats()
            self.print_distribution(self.domains, "Domain", 50)
            self.print_distribution(self.dns_servers, "DNS Server", 20)
            self.print_distribution(self.sites, "Site", 20)
            self.print_distribution(self.devices, "Device", 50)
            self.print_distribution(self.device_manufacturers, "Device Manufacturer", 20)
            self.print_distribution(self.device_os, "Device OS", 20)
            self.print_distribution(self.vlans, "VLAN", 20)
            self.print_hourly_distribution()
            
            # Restore stdout
            sys.stdout = original_stdout
        
        print(f"\nAnalysis exported to: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Analyze DNS failure CSV data')
    parser.add_argument('csv_file', help='Path to the CSV file containing DNS failure data')
    parser.add_argument('-n', '--top', type=int, default=20, 
                        help='Number of top entries to show (default: 20)')
    parser.add_argument('-o', '--output', help='Output file to save analysis results')
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = DNSFailureAnalyzer(args.csv_file)
    
    # Perform analysis
    analyzer.analyze(top_n=args.top)
    
    # Export if requested
    if args.output:
        analyzer.export_analysis(args.output)

if __name__ == "__main__":
    main()