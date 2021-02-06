import React from 'react';
import ReactDOM from 'react-dom';
import './style.css';
import { FocusStyleManager } from '@blueprintjs/core';
import { BrowserRouter } from 'react-router-dom';

import Page from './components/page';
import { GlobalState, StateProvider } from './lib/state';

FocusStyleManager.onlyShowFocusOnTabs();

ReactDOM.render(
  <StateProvider value={new GlobalState({})}>
    <BrowserRouter>
      <Page />
    </BrowserRouter>
  </StateProvider>,
  document.querySelector('#container'),
);

if (process.env.NODE_ENV === 'development') {
  const chan = new EventSource('/events');
  chan.addEventListener('message', (e) => {
    if (e.data === 'ready') {
      console.log('[LR] Ready');
    } else if (e.data === 'reload') {
      console.log('[LR] Reloading...');
      location.reload();
    } else {
      console.log(`[LR] ${e.data}`);
    }
  });
}
