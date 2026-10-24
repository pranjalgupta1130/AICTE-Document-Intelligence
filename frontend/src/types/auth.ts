export type RoleKey = 'admin' | 'operator' | 'reviewer' | 'verifier' | 'evaluator';

export interface RoleData {
  key: RoleKey;
  shortTitle: string;
  subtitle: string;
  icon: string;
  title: string;
  tag: string;
  tagClass: string;
  description: string;
  email: string;
  pid: string;
  pwd: string;
}

export interface AuthCredentials {
  username: string;
  instCode: string;
  password: string;
  enableDigiLocker: boolean;
  bindHardwareTerminal: boolean;
}

export interface AuthSession {
  token: string;
  role: RoleKey;
  roleTitle: string;
  instCode: string;
  userEmail: string;
  timestamp: string;
  expiresIn: string;
}
