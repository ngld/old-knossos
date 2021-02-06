import React, {useContext} from 'react';
import {observer} from 'mobx-react-lite';
import {Button, IButtonProps} from '@blueprintjs/core';
import {FormContext} from './form-ctx';

interface ButtonProps extends IButtonProps {
  children?: React.ReactNode | React.ReactNode[];
}

export default observer(function FormButton(props: ButtonProps) {
  const ctx = useContext(FormContext);
  const disabled = props.disabled ?? ctx?.defaults.disabled;

  return <Button {...props} disabled={disabled} />;
});
