/** Mirrors apps/accounts/serializers.py's UserSerializer — the
 * DRF-authoritative counterpart to allauth's session envelope
 * (features/auth/types.ts), used for role/profile-completion state that
 * allauth itself knows nothing about. */
export interface Me {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
  date_joined: string;
  roles: string[];
  is_customer: boolean;
  profile_completed: boolean;
}
