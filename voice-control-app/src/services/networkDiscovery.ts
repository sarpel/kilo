import { Platform } from 'react-native';
import NetInfo from '@react-native-community/netinfo';
import { VoiceControlNativeModule } from '../native/VoiceControlNativeModule';

export interface DiscoveredServer {
  address: string;
  port: number;
  hostname?: string;
  responseTime: number;
  isReachable: boolean;
}

export interface NetworkInfo {
  ipAddress: string;
  gateway: string;
  subnetMask: string;
  interfaceType: string; // wifi, ethernet, cellular
  isConnected: boolean;
}

export class NetworkDiscoveryService {
  private static instance: NetworkDiscoveryService;
  private discoveredServers: DiscoveredServer[] = [];
  private isScanning = false;
  private scanTimeout: NodeJS.Timeout | null = null;

  private constructor() {
    this.setupNetworkListeners();
  }

  public static getInstance(): NetworkDiscoveryService {
    if (!NetworkDiscoveryService.instance) {
      NetworkDiscoveryService.instance = new NetworkDiscoveryService();
    }
    return NetworkDiscoveryService.instance;
  }

  /**
   * Discover voice control servers on the local network
   */
  public async discoverServers(timeoutMs: number = 10000): Promise<DiscoveredServer[]> {
    if (this.isScanning) {
      console.log('Network discovery already in progress');
      return this.discoveredServers;
    }

    this.isScanning = true;
    this.discoveredServers = [];

    try {
      // Get network information
      const networkInfo = await this.getNetworkInfo();
      if (!networkInfo.isConnected) {
        throw new Error('No network connection available');
      }

      // Generate potential server addresses
      const potentialAddresses = this.generatePotentialAddresses(networkInfo);
      
      // Scan each potential address
      const scanPromises = potentialAddresses.map(address => 
        this.pingServer(address, 8000, timeoutMs)
      );

      // Wait for all scans to complete or timeout
      const results = await Promise.allSettled(scanPromises);
      
      // Filter successful results
      this.discoveredServers = results
        .filter((result): result is PromiseFulfilledResult<DiscoveredServer> => 
          result.status === 'fulfilled' && result.value.isReachable
        )
        .map(result => result.value)
        .sort((a, b) => a.responseTime - b.responseTime);

      console.log(`Found ${this.discoveredServers.length} voice control servers`);
      return this.discoveredServers;

    } catch (error) {
      console.error('Server discovery failed:', error);
      throw error;
    } finally {
      this.isScanning = false;
    }
  }

  /**
   * Test connectivity to a specific server address
   */
  public async testServer(address: string, port: number = 8000): Promise<boolean> {
    try {
      // Try native module first (Android)
      if (Platform.OS === 'android') {
        const result = await VoiceControlNativeModule.pingServer(`${address}:${port}`);
        return result;
      }

      // Fallback to manual ping simulation
      const startTime = Date.now();
      const controller = new AbortController();
      
      // Set timeout
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      
      try {
        const response = await fetch(`http://${address}:${port}/health`, {
          method: 'GET',
          signal: controller.signal,
          headers: {
            'Content-Type': 'application/json',
          },
        });
        
        clearTimeout(timeoutId);
        const responseTime = Date.now() - startTime;
        
        return response.ok;
      } catch (fetchError) {
        clearTimeout(timeoutId);
        
        // Try WebSocket connection as fallback
        const ws = new WebSocket(`ws://${address}:${port}/ws`);
        
        return new Promise((resolve) => {
          ws.onopen = () => {
            ws.close();
            resolve(true);
          };
          
          ws.onerror = () => {
            resolve(false);
          };
          
          ws.onclose = () => {
            resolve(false);
          };
          
          // Timeout fallback
          setTimeout(() => {
            ws.close();
            resolve(false);
          }, 3000);
        });
      }
    } catch (error) {
      console.error(`Failed to test server ${address}:${port}:`, error);
      return false;
    }
  }

  /**
   * Get current network information
   */
  public async getNetworkInfo(): Promise<NetworkInfo | null> {
    try {
      if (Platform.OS === 'android') {
        const nativeInfo = await VoiceControlNativeModule.getNetworkInfo();
        if (nativeInfo) {
          return {
            ipAddress: nativeInfo.ip,
            gateway: nativeInfo.gateway || '',
            subnetMask: nativeInfo.subnet || '',
            interfaceType: nativeInfo.type || 'unknown',
            isConnected: nativeInfo.connected,
          };
        }
      }

      // Fallback to NetInfo
      const state = await NetInfo.fetch();
      
      // Extract IP from details if available
      const ipAddress = this.extractIPFromState(state);
      
      return {
        ipAddress: ipAddress || 'unknown',
        gateway: '',
        subnetMask: '',
        interfaceType: state.type || 'unknown',
        isConnected: state.isConnected ?? false,
      };
    } catch (error) {
      console.error('Failed to get network info:', error);
      return null;
    }
  }

  /**
   * Ping a server and measure response time
   */
  private async pingServer(address: string, port: number, timeoutMs: number): Promise<DiscoveredServer> {
    const startTime = Date.now();
    const isReachable = await this.testServer(address, port);
    const responseTime = Date.now() - startTime;

    return {
      address,
      port,
      hostname: address,
      responseTime,
      isReachable,
    };
  }

  /**
   * Generate potential server addresses based on network info
   */
  private generatePotentialAddresses(networkInfo: NetworkInfo): string[] {
    const addresses: string[] = [];
    
    if (networkInfo.ipAddress && networkInfo.ipAddress !== 'unknown') {
      // Generate addresses by incrementing the last octet
      const parts = networkInfo.ipAddress.split('.');
      if (parts.length === 4) {
        const baseAddress = parts.slice(0, 3).join('.');
        
        // Common server IP patterns
        for (let i = 1; i <= 254; i++) {
          if (i === parseInt(parts[3])) {
            continue; // Skip current device IP
          }
          
          addresses.push(`${baseAddress}.${i}`);
          
          // Limit to common server addresses
          if (addresses.length > 50) {
            break;
          }
        }
        
        // Add common server IPs
        const commonAddresses = [
          '192.168.1.1',    // Router
          '192.168.1.10',
          '192.168.1.100',
          '192.168.1.101',
          '192.168.1.200',
          '10.0.0.1',       // Alternative networks
          '10.0.0.100',
        ];
        
        addresses.push(...commonAddresses);
      }
    }
    
    return [...new Set(addresses)]; // Remove duplicates
  }

  /**
   * Extract IP address from NetInfo state
   */
  private extractIPFromState(state: any): string | null {
    if (state.details && state.details.ipAddress) {
      return state.details.ipAddress;
    }
    
    // Try other possible locations for IP
    if (state.connectionInfo && state.connectionInfo.localIp) {
      return state.connectionInfo.localIp;
    }
    
    return null;
  }

  /**
   * Setup network change listeners
   */
  private setupNetworkListeners(): void {
    NetInfo.addEventListener(state => {
      console.log('Network state changed:', {
        isConnected: state.isConnected,
        type: state.type,
        isInternetReachable: state.isInternetReachable,
      });
      
      // Clear discovered servers when network changes
      if (state.isConnected === false) {
        this.discoveredServers = [];
      }
    });
  }

  /**
   * Get the last discovered servers
   */
  public getDiscoveredServers(): DiscoveredServer[] {
    return this.discoveredServers;
  }

  /**
   * Clear the discovered servers cache
   */
  public clearCache(): void {
    this.discoveredServers = [];
  }

  /**
   * Check if discovery is currently in progress
   */
  public isDiscoveryInProgress(): boolean {
    return this.isScanning;
  }

  /**
   * Cancel ongoing discovery
   */
  public cancelDiscovery(): void {
    if (this.scanTimeout) {
      clearTimeout(this.scanTimeout);
      this.scanTimeout = null;
    }
    this.isScanning = false;
  }
}

export default NetworkDiscoveryService;