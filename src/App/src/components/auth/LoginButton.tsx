import React, { useCallback } from 'react';
import {
  Avatar,
  Menu,
  MenuTrigger,
  MenuPopover,
  MenuList,
  MenuItem,
  Button,
  makeStyles,
  tokens,
} from '@fluentui/react-components';
import { Person20Regular, SignOut24Regular } from '@fluentui/react-icons';
import { useAppSelector } from '../../store/hooks';

const useStyles = makeStyles({
  userButton: {
    minWidth: 'auto',
    paddingLeft: tokens.spacingHorizontalXS,
    paddingRight: tokens.spacingHorizontalXS,
  },
  menuItem: {
    paddingLeft: tokens.spacingHorizontalM,
    paddingRight: tokens.spacingHorizontalM,
  },
  userInfo: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: tokens.spacingVerticalXXS,
  },
  userName: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: tokens.fontSizeBase200,
  },
  userEmail: {
    fontSize: tokens.fontSizeBase100,
    color: tokens.colorNeutralForeground2,
  },
  triggerContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: tokens.spacingHorizontalS,
    cursor: 'pointer',
  },
  displayName: {
    fontSize: tokens.fontSizeBase300,
    fontWeight: tokens.fontWeightSemibold,
    color: tokens.colorNeutralForeground1,
  },
});

const getUserInitials = (name: string | undefined): string => {
  if (!name) return 'U';
  const cleanName = name.replace(/\s*\([^)]*\)/g, '').trim();
  if (!cleanName) return 'U';
  const parts = cleanName.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return cleanName.charAt(0).toUpperCase();
};

interface LoginButtonProps {
  showName?: boolean;
}

const LoginButton: React.FC<LoginButtonProps> = ({ showName = false }) => {
  const styles = useStyles();
  const userName = useAppSelector(state => state.app.userName);
  const userId = useAppSelector(state => state.app.userId);
  const userEmail = useAppSelector(state => state.app.userEmail);
  const isAuthenticated = Boolean(userId && userId !== 'anonymous');

  const login = useCallback(() => {
    window.location.href = '/.auth/login/aad';
  }, []);

  const logout = useCallback(() => {
    const logoutUrl = '/.auth/logout?post_logout_redirect_uri=' + encodeURIComponent('/.auth/login/aad');
    window.location.href = logoutUrl;
  }, []);

  const displayName = isAuthenticated ? userName || userId || 'User' : 'User';

  if (!isAuthenticated) {
    return (
      <div className={styles.triggerContainer} style={{ cursor: 'default' }}>
        <Avatar
          name="Guest"
          initials="G"
          size={28}
          color="colorful"
          style={{ fontWeight: 'bold' }}
        />
        {showName && <span className={styles.displayName}>Guest</span>}
      </div>
    );
  }

  return (
    <Menu positioning="above-end">
      <MenuTrigger disableButtonEnhancement>
        <div className={styles.triggerContainer} role="button" tabIndex={0} title={`Signed in as ${displayName}`}>
          <Avatar
            name={displayName}
            initials={getUserInitials(displayName)}
            size={28}
            color="colorful"
            style={{ fontWeight: 'bold' }}
          />
          {showName && <span className={styles.displayName}>{displayName}</span>}
        </div>
      </MenuTrigger>

      <MenuPopover>
        <MenuList>
          <MenuItem className={styles.menuItem} icon={<Person20Regular />} disabled style={{ cursor: 'default' }}>
            <div className={styles.userInfo}>
              <div className={styles.userName}>{displayName}</div>
              {userEmail && <div className={styles.userEmail}>{userEmail}</div>}
            </div>
          </MenuItem>
          <MenuItem
            className={styles.menuItem}
            icon={<SignOut24Regular />}
            onClick={logout}
          >
            Sign out
          </MenuItem>
        </MenuList>
      </MenuPopover>
    </Menu>
  );
};

export default LoginButton;
