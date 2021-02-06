import { createContext } from 'react';

export type FormState = Record<string, string>;

export interface DefaultOptions {
  inline?: boolean;
  disabled?: boolean;
  spinning?: boolean;
}

export interface FormContextType {
  state: FormState;
  uid: string;
  defaults: DefaultOptions;
  errors: Record<string, string | undefined>;
}

export const FormContext = createContext<FormContextType | null>(null);
