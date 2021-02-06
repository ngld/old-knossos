import React, { useContext } from 'react';
import { action } from 'mobx';
import { observer } from 'mobx-react-lite';
import { FormGroup, InputGroup, IconName, MaybeElement, Intent } from '@blueprintjs/core';
import { FormContext } from './form-ctx';

interface Props {
  name: string;
  label: string;
  required?: boolean;
  disabled?: boolean;
  helperText?: string;
  inline?: boolean;

  placeholder?: string;
  intent?: Intent;
  fill?: boolean;
  round?: boolean;
  type?: string;
  leftElement?: React.ReactElement;
  rightElement?: React.ReactElement;
  leftIcon?: IconName | MaybeElement;
}

export default observer(function Field(props: Props): React.ReactElement {
  const ctx = useContext(FormContext);
  if (ctx === null) {
    throw new Error('FormContext is missing!');
  }

  const id = `${ctx.uid}-${props.name}`;
  let info = props.required ? 'required' : '';
  let intent = props.intent;
  let helperText: React.ReactNode = props.helperText;
  const disabled = props.disabled ?? ctx.defaults.disabled;

  if (!intent && ctx.errors[props.name]) {
    intent = 'danger';
    if (helperText) {
      helperText = (
        <span>
          {ctx.errors[props.name]}
          <br />
          {helperText}
        </span>
      );
    } else {
      helperText = ctx.errors[props.name];
    }
  }
  return (
    <FormGroup
      helperText={helperText}
      label={props.label}
      labelFor={id}
      labelInfo={info}
      disabled={disabled}
      inline={ctx.defaults.inline}
      intent={intent}
    >
      <InputGroup
        id={id}
        placeholder={props.placeholder}
        disabled={disabled}
        fill={props.fill}
        round={props.round}
        type={props.type ?? 'text'}
        leftElement={props.leftElement}
        rightElement={props.rightElement}
        leftIcon={props.leftIcon}
        intent={intent}
        value={ctx.state[props.name]}
        onChange={action((ev) => {
          ctx.state[props.name] = ev.target.value;
        })}
      />
    </FormGroup>
  );
});
