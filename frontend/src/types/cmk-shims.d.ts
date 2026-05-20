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
    export interface Suggestion {
        name: string | null;
        title: string;
    }
    export interface SuggestionsFixed {
        type: 'fixed';
        suggestions: Suggestion[];
    }
    interface CmkDropdownProps {
        options:
            | SuggestionsFixed
            | { type: 'filtered'; suggestions: Suggestion[] }
            | { type: 'callback-filtered'; querySuggestions: (q: string) => Promise<unknown> };
        label: string;
        selectedOption?: string | null;
        disabled?: boolean;
        required?: boolean;
        inputHint?: string;
        noResultsHint?: string;
        noElementsText?: string;
        width?: 'default' | 'half' | 'fill';
        formValidation?: boolean;
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

declare module '@cmk/components/CmkBadge.vue' {
    import type { DefineComponent } from 'vue';
    interface CmkBadgeProps {
        size?: 'small' | 'medium' | 'large';
        color?: 'default' | 'success' | 'warning' | 'danger';
        type?: 'fill' | 'outline';
        shape?: 'default' | 'circle';
    }
    const component: DefineComponent<CmkBadgeProps>;
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

declare module '@cmk/components/CmkHelpText.vue' {
    import type { DefineComponent } from 'vue';
    interface CmkHelpTextProps {
        help: string;
        ariaLabel?: string;
    }
    const component: DefineComponent<CmkHelpTextProps>;
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

declare module '@cmk/components/CmkScrollContainer.vue' {
    import type { DefineComponent } from 'vue';
    interface CmkScrollContainerProps {
        maxHeight?: string;
        height?: string;
        type?: 'inner' | 'outer';
    }
    const component: DefineComponent<CmkScrollContainerProps>;
    export default component;
}

declare module '@cmk/components/CmkToggleButtonGroup.vue' {
    import type { DefineComponent } from 'vue';
    interface ToggleButtonOption {
        label: string;
        value: string;
        disabled?: boolean | string;
    }
    interface CmkToggleButtonGroupProps {
        options: ToggleButtonOption[];
        modelValue?: string | null;
    }
    const component: DefineComponent<
        CmkToggleButtonGroupProps,
        object,
        object,
        object,
        object,
        object,
        object,
        { 'update:modelValue': [value: string] }
    >;
    export default component;
}

declare module '@cmk/components/CmkTabs/CmkTabs.vue' {
    import type { DefineComponent } from 'vue';
    const component: DefineComponent<object>;
    export default component;
}

declare module '@cmk/components/CmkTabs/CmkTab.vue' {
    import type { DefineComponent } from 'vue';
    interface CmkTabProps {
        id: string;
        disabled?: boolean;
        variant?: 'default' | 'info' | 'success' | 'warning' | 'error';
    }
    const component: DefineComponent<CmkTabProps>;
    export default component;
}

declare module '@cmk/components/CmkTabs/CmkTabContent.vue' {
    import type { DefineComponent } from 'vue';
    interface CmkTabContentProps {
        id: string;
        spacing?: 'default' | 'none';
    }
    const component: DefineComponent<CmkTabContentProps>;
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

declare module '@cmk/components/CmkDialog.vue' {
    import type { DefineComponent } from 'vue';
    type ButtonVariant =
        | 'primary'
        | 'secondary'
        | 'optional'
        | 'success'
        | 'warning'
        | 'danger'
        | 'info';
    interface CmkDialogProps {
        title?: string;
        message: string;
        buttons?: { title: string; variant: ButtonVariant; onclick: () => void }[];
        variant?: 'error' | 'warning' | 'success' | 'info' | 'loading';
    }
    const component: DefineComponent<CmkDialogProps>;
    export default component;
}

declare module '@cmk/components/CmkIcon/CmkMultitoneIcon.vue' {
    import type { DefineComponent } from 'vue';
    interface CmkMultitoneIconProps {
        name: string;
        primaryColor?: { custom: string } | { variable: string };
        size?: 'xsmall' | 'small' | 'medium' | 'large' | 'xlarge' | 'xxlarge' | 'xxxlarge';
        title?: string;
    }
    const component: DefineComponent<CmkMultitoneIconProps>;
    export default component;
}

declare module '@cmk/components/CmkIcon' {
    import type { DefineComponent } from 'vue';
    interface CmkIconProps {
        name: string;
        size?: 'xsmall' | 'small' | 'medium' | 'large' | 'xlarge' | 'xxlarge' | 'xxxlarge';
        title?: string;
        rotate?: number;
        variant?: 'inline' | 'plain';
        colored?: 'colored' | 'colorless';
    }
    const component: DefineComponent<CmkIconProps>;
    export default component;
}

declare module '@cmk/components/CmkPopup.vue' {
    import type { DefineComponent } from 'vue';
    interface CmkPopupProps {
        open: boolean;
    }
    const component: DefineComponent<
        CmkPopupProps,
        object,
        object,
        object,
        object,
        object,
        object,
        { close: [] }
    >;
    export default component;
}

declare module '@cmk/components/CmkPopupDialog.vue' {
    import type { DefineComponent } from 'vue';
    interface CmkPopupDialogProps {
        open: boolean;
        icon?: string;
        title: string;
        text?: string;
        okButtonText?: string;
        stayOpenOverlayClick?: boolean;
    }
    const component: DefineComponent<
        CmkPopupDialogProps,
        object,
        object,
        object,
        object,
        object,
        object,
        { close: [] }
    >;
    export default component;
}

declare module '@cmk/components/typography/CmkHeading.vue' {
    import type { DefineComponent } from 'vue';
    interface CmkHeadingProps {
        type?: 'h1' | 'h2' | 'h3' | 'h4';
        onClick?: (() => void) | null;
    }
    const component: DefineComponent<CmkHeadingProps>;
    export default component;
}

declare module '@cmk/components/typography/CmkParagraph.vue' {
    import type { DefineComponent } from 'vue';
    const component: DefineComponent<object>;
    export default component;
}

declare module '@cmk/components/CmkSlideInDialog.vue' {
    import type { DefineComponent } from 'vue';
    interface CmkSlideInDialogProps {
        open: boolean;
        size?: 'small' | 'medium' | 'large';
        isIndexPage?: boolean;
        stackPriority?: number;
        header?: {
            title: string;
            icon?: { name: string; size?: string };
            closeButton: boolean;
        };
        borderColor?: 'default' | 'success' | 'warning' | 'danger' | 'info';
    }
    const component: DefineComponent<
        CmkSlideInDialogProps,
        object,
        object,
        object,
        object,
        object,
        object,
        { close: [] }
    >;
    export default component;
}

declare module '@cmk/components/CmkLinkCard/CmkLinkCard.vue' {
    import type { DefineComponent } from 'vue';
    interface CmkLinkCardProps {
        iconName?: string;
        title: string;
        subtitle?: string;
        url?: string;
        callback?: () => void;
        openInNewTab: boolean;
        disabled?: boolean;
        borders?: 'standard' | 'borderless';
        contrast?: 'standard' | 'high';
    }
    const component: DefineComponent<CmkLinkCardProps>;
    export default component;
}

declare module '@cmk/components/CmkLinkCard/CmkLinkCardContainer.vue' {
    import type { DefineComponent } from 'vue';
    interface CmkLinkCardContainerProps {
        orientation?: 'vertical' | 'horizontal';
    }
    const component: DefineComponent<CmkLinkCardContainerProps>;
    export default component;
}

declare module '@cmk/form/FormApp.vue' {
    import type { VueFormspecComponents } from 'cmk-shared-typing/typescript/vue_formspec_components';
    import type { DefineComponent } from 'vue';
    type Spec = NonNullable<VueFormspecComponents['components']>;
    type Validation = NonNullable<VueFormspecComponents['validation_message']>[];
    interface FormAppProps {
        id: string;
        spec: Spec;
        data: unknown;
        validation: Validation;
        display_mode: 'edit' | 'readonly' | 'both';
    }
    const component: DefineComponent<FormAppProps>;
    export default component;
}

declare module '@cmk/form/FormEdit.vue' {
    import type { VueFormspecComponents } from 'cmk-shared-typing/typescript/vue_formspec_components';
    import type { DefineComponent } from 'vue';
    type Spec = NonNullable<VueFormspecComponents['components']>;
    type Validation = NonNullable<VueFormspecComponents['validation_message']>[];
    interface FormEditProps {
        spec: Spec;
        data: unknown;
        backendValidation: Validation;
    }
    const component: DefineComponent<
        FormEditProps,
        object,
        object,
        object,
        object,
        object,
        object,
        { 'update:data': [value: unknown] }
    >;
    export default component;
}

declare module '@cmk/form/private/FormEditDispatcher/dispatch' {
    import type { Component } from 'vue';
    export function initializeComponentRegistry(extra?: Record<string, Component>): void;
    export function getComponent(type: string): unknown;
}

declare module '@cmk/form/private/forms/FormOrbColor.vue' {
    import type { DefineComponent } from 'vue';
    const component: DefineComponent<Record<string, unknown>>;
    export default component;
}

declare module '@cmk/components/user-input/CmkLabelRequired.vue' {
    import type { DefineComponent } from 'vue';
    interface CmkLabelRequiredProps {
        show?: boolean;
        space?: 'before' | 'after' | 'both' | null;
    }
    const component: DefineComponent<CmkLabelRequiredProps>;
    export default component;
}
