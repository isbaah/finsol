/** Mirrors django-allauth headless's response envelope. See
 * backend/config/settings/base.py's authentication section and
 * docs/BUILD_PROGRESS.md's Stage 2 notes for how this was verified against
 * the installed django-allauth==65.18.0 source. */

export interface AllauthUser {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
}

export interface AllauthFlow {
  id: string;
  is_pending?: boolean;
  providers?: string[];
  types?: string[];
}

export interface AllauthFieldError {
  message: string;
  code: string;
  param?: string;
}

export interface AllauthEnvelope {
  status: number;
  data?: {
    user?: AllauthUser;
    flows?: AllauthFlow[];
  };
  meta?: {
    is_authenticated: boolean;
  };
  errors?: AllauthFieldError[];
}

export interface SessionState {
  isAuthenticated: boolean;
  user: AllauthUser | null;
  pendingFlow: AllauthFlow | null;
}
