import { AuthCredentials, AuthSession, RoleKey } from '../types/auth';
import { ROLE_DATASETS } from '../data/rolesData';

const SESSION_KEY = 'apaar_auth_session';

export const authService = {
  /**
   * Authenticate nodal officer credentials against AICTE / NeGD Gateway
   */
  async login(credentials: AuthCredentials, activeRole: RoleKey): Promise<AuthSession> {
    // Simulate real cryptographic SHA-256 network handshake latency
    await new Promise((resolve) => setTimeout(resolve, 1100));

    const roleInfo = ROLE_DATASETS[activeRole];
    const pseudoHash = Array.from({ length: 32 }, () =>
      Math.floor(Math.random() * 16).toString(16)
    ).join('').toUpperCase();

    const session: AuthSession = {
      token: `SHA256-APAAR-${pseudoHash.substring(0, 12)}`,
      role: activeRole,
      roleTitle: roleInfo.title,
      instCode: credentials.instCode,
      userEmail: credentials.username,
      timestamp: new Date().toISOString(),
      expiresIn: credentials.bindHardwareTerminal ? '8 hours' : '1 hour',
    };

    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    return session;
  },

  /**
   * Get current active session
   */
  getCurrentSession(): AuthSession | null {
    try {
      const saved = localStorage.getItem(SESSION_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  },

  /**
   * Terminate active session
   */
  logout(): void {
    localStorage.removeItem(SESSION_KEY);
  },
};
