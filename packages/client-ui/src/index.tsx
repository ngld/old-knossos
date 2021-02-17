import React from 'react';
import ReactDOM from 'react-dom';
import './style.css';
import { FocusStyleManager, H1 } from '@blueprintjs/core';
// import { BrowserRouter } from 'react-router-dom';

FocusStyleManager.onlyShowFocusOnTabs();

ReactDOM.render(
  <H1>Hello Knossos!</H1>,
  document.querySelector('#container'),
);

