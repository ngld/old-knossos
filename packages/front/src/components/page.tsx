import React from 'react';
import {
  H1,
  Navbar,
  NavbarGroup,
  NavbarHeading,
  NavbarDivider,
  Menu,
  MenuDivider,
  MenuItem,
  Button,
} from '@blueprintjs/core';
import { Popover2 } from '@blueprintjs/popover2';
import { Switch, Route, useHistory } from 'react-router-dom';
import { Observer } from 'mobx-react-lite';

import { useGlobalState } from '../lib/state';
import { AlertContainer } from '../lib/alert';
import Register from '../pages/register';
import Login from '../pages/login';
import ResetPassword from '../pages/reset-password';
import ResetPasswordContinued from '../pages/reset-password-continue';
import Logout from '../pages/logout';
import ModList from '../pages/mods/list';

interface Props {
  children?: React.ReactNode | React.ReactNode[];
}

export default function Page(_props: Props): React.ReactElement {
  const gs = useGlobalState();
  const history = useHistory();

  return (
    <>
      <Navbar>
        <div className="mx-auto max-w-screen-lg w-full">
          <NavbarGroup>
            <NavbarHeading>Neo Nebula</NavbarHeading>
            <NavbarDivider />
            <Button minimal icon="home" text="Home" onClick={() => history.push('/')} />
            <Button minimal icon="widget" text="Mods" onClick={() => history.push('/mods')} />
            <Popover2
              placement="bottom"
              minimal
              content={
                <Menu>
                  <MenuItem icon="plus" text="Create Mod" />
                  <MenuItem icon="people" text="My Mods" />
                </Menu>
              }
            >
              <Button minimal icon="chevron-down" />
            </Popover2>
          </NavbarGroup>
          <NavbarGroup align="right">
            <Observer>
              {() =>
                gs.user?.loggedIn ? (
                  <>
                    {gs.user.username}
                    <Button minimal={true} icon="log-out" onClick={() => history.push('/logout')}>
                      Logout
                    </Button>
                  </>
                ) : (
                  <>
                    <Button minimal={true} icon="log-in" onClick={() => history.push('/login')}>
                      Login
                    </Button>
                    <Button minimal={true} icon="key" onClick={() => history.push('/register')}>
                      Register
                    </Button>
                  </>
                )
              }
            </Observer>
          </NavbarGroup>
        </div>
      </Navbar>

      <div className="container py-5 max-w-screen-lg mx-auto">
        <Switch>
          <Route exact path="/">
            <H1>Welcome back!</H1>
            <p>Well, here we go again...</p>
            <p>Let's hope this attempt works out better than last time.</p>
          </Route>
          <Route exact path="/register" component={Register} />
          <Route exact path="/login" component={Login} />
          <Route exact path="/login/reset-password" component={ResetPassword} />
          <Route exact path="/mail/reset/:token" component={ResetPasswordContinued} />
          <Route exact path="/logout" component={Logout} />
          <Route exact path="/mods" component={ModList} />
          <Route path="*">
            <H1>Not Found</H1>
            <p>I'm sorry but I could not find what you're looking for.</p>
          </Route>
        </Switch>
      </div>

      <AlertContainer />
    </>
  );
}
