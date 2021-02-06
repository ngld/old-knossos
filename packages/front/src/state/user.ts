import { model, Model, prop, modelAction, modelFlow, _async, _await } from 'mobx-keystone';
import type { GlobalState } from '../lib/state';
import type { SessionResponse } from '@api/service';

@model('nebula/User')
export class User extends Model({
  loggedIn: prop(false),
  token: prop<string>(),
  username: prop<string>(),
}) {
  _g?: GlobalState;

  onAttachedToRootStore(root: GlobalState) {
    this._g = root;

    if (window.localStorage) {
      const token = localStorage.getItem('nebula_token');
      if (token && token !== '') {
        void this.login(token);
      }
    }
  }

  @modelFlow
  login = _async(function* (this: User, token: string) {
    let response: SessionResponse | undefined;
    const g = this._g;
    if (!g || !g.client) {
      throw new Error('Called User.login() before attaching it to the root store!');
    }

    this.token = token;
    try {
      response = yield* _await(g.runTwirpRequest(g.client.checkToken, {}, undefined, true));
    } catch (e) {
      console.log(e);
      this.token = '';
      return;
    }

    if (response?.valid) {
      this.token = token;
      this.username = response.username;
      this.loggedIn = true;

      if (window.localStorage) {
        localStorage.setItem('nebula_token', token);
      }
    } else {
      this.token = '';
    }
  });

  @modelAction
  logout() {
    this.token = '';
    this.username = '';
    this.loggedIn = false;

    if (window.localStorage) {
      localStorage.setItem('nebula_token', '');
    }
  }
}
