declare module '@cmk/components/CmkButton.vue' {
  import type { DefineComponent } from 'vue';
  type ButtonVariant =
    | 'primary'
    | 'secondary'
    | 'optional'
    | 'success'
    | 'warning'
    | 'danger'
    | 'info';
  interface CmkButtonProps {
    variant?: ButtonVariant;
    disabled?: boolean | string;
    title?: string;
    href?: string;
    target?: string;
  }
  const component: DefineComponent<CmkButtonProps>;
  export default component;
}

declare module '@cmk/components/user-input/CmkInput.vue' {
  import type { DefineComponent } from 'vue';
  interface CmkInputProps {
    modelValue?: string | number | null;
    type?: 'text' | 'number' | 'date' | 'time' | 'password';
    placeholder?: string;
    disabled?: boolean;
    autocomplete?: string;
    fieldSize?: 'SMALL' | 'MEDIUM' | 'LARGE' | 'FILL';
  }
  const component: DefineComponent<
    CmkInputProps,
    object,
    object,
    object,
    object,
    object,
    object,
    { 'update:modelValue': [value: string | number | null] }
  >;
  export default component;
}

declare module '@cmk/components/user-input/CmkCheckbox.vue' {
  import type { DefineComponent } from 'vue';
  interface CmkCheckboxProps {
    modelValue?: boolean;
    label?: string;
    disabled?: boolean;
  }
  const component: DefineComponent<
    CmkCheckboxProps,
    object,
    object,
    object,
    object,
    object,
    object,
    { 'update:modelValue': [value: boolean] }
  >;
  export default component;
}

declare module '@cmk/components/CmkDropdown/CmkDropdown.vue' {
  import type { DefineComponent } from 'vue';
  interface Suggestion {
    name: string;
    title: string;
  }
  interface CmkDropdownProps {
    selectedOption?: string | null;
    options?: Suggestion[] | ((value: string) => Promise<Suggestion[]>);
    label?: string;
    disabled?: boolean;
    noResultsText?: string;
    placeholder?: string;
  }
  const component: DefineComponent<
    CmkDropdownProps,
    object,
    object,
    object,
    object,
    object,
    object,
    { 'update:selectedOption': [value: string | null] }
  >;
  export default component;
}

declare module '@cmk/components/CmkAlertBox.vue' {
  import type { DefineComponent } from 'vue';
  type AlertBoxVariant = 'error' | 'warning' | 'success' | 'info' | 'loading';
  type AlertBoxSize = 'small' | 'medium';
  interface CmkAlertBoxProps {
    variant?: AlertBoxVariant;
    size?: AlertBoxSize;
    heading?: string;
    autoDismiss?: boolean;
    dismissible?: boolean;
  }
  const component: DefineComponent<CmkAlertBoxProps>;
  export default component;
}

declare module '@cmk/components/CmkLoading.vue' {
  import type { DefineComponent } from 'vue';
  interface CmkLoadingProps {
    height?: string;
  }
  const component: DefineComponent<CmkLoadingProps>;
  export default component;
}

declare module '@cmk/components/CmkSwitch.vue' {
  import type { DefineComponent } from 'vue';
  const component: DefineComponent<
    object,
    object,
    object,
    object,
    object,
    object,
    object,
    { 'update:data': [value: boolean] }
  >;
  export default component;
}

declare module '@cmk/components/CmkCollapsible/CmkCollapsible.vue' {
  import type { DefineComponent } from 'vue';
  interface CmkCollapsibleProps {
    open: boolean;
    contentId?: string;
  }
  const component: DefineComponent<CmkCollapsibleProps>;
  export default component;
}

declare module '@cmk/components/CmkCollapsible/CmkCollapsibleTitle.vue' {
  import type { TranslatedString } from '@cmk/lib/i18nString';
  import type { DefineComponent } from 'vue';
  interface CmkCollapsibleTitleProps {
    title: TranslatedString;
    open: boolean;
    sideTitle?: TranslatedString;
    disabled?: boolean;
  }
  const component: DefineComponent<
    CmkCollapsibleTitleProps,
    object,
    object,
    object,
    object,
    object,
    object,
    { toggleOpen: [] }
  >;
  export default component;
}

declare module '@cmk/components/CmkColorPicker.vue' {
  import type { DefineComponent } from 'vue';
  const component: DefineComponent<
    object,
    object,
    object,
    object,
    object,
    object,
    object,
    { 'update:data': [value: string] }
  >;
  export default component;
}

declare module '@cmk/components/CmkLabel.vue' {
  import type { DefineComponent } from 'vue';
  interface CmkLabelProps {
    for?: string;
    variant?: 'default' | 'title' | 'subtitle';
    dots?: boolean;
  }
  const component: DefineComponent<CmkLabelProps>;
  export default component;
}
