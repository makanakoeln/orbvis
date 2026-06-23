#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# This file is auto-generated via the cmk-shared-typing package.
# Do not edit manually.
#
# fmt: off
# ruff: noqa: UP007, UP035, UP042, UP045  # vendored verbatim from cmk-shared-typing (CMK 2.6); keep upstream typing style so the drift-check stays byte-for-byte.


from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import Any, Literal, Mapping, Optional, Sequence, Union


@dataclass(frozen=True, kw_only=True)
class IsInteger:
    error_message: str
    type: Literal["is_integer"] = "is_integer"


@dataclass(frozen=True, kw_only=True)
class IsFloat:
    error_message: str
    type: Literal["is_float"] = "is_float"


@dataclass(frozen=True, kw_only=True)
class LengthInRange:
    min_value: Optional[int]
    max_value: Optional[int]
    error_message: str
    type: Literal["length_in_range"] = "length_in_range"


@dataclass(frozen=True, kw_only=True)
class NumberInRange:
    min_value: Optional[float]
    max_value: Optional[float]
    error_message: str
    type: Literal["number_in_range"] = "number_in_range"


@dataclass(frozen=True, kw_only=True)
class MatchRegex:
    type: Literal["match_regex"] = "match_regex"
    regex: Optional[str] = None
    error_message: Optional[str] = None


type Validator = Union[IsInteger, IsFloat, NumberInRange, LengthInRange, MatchRegex]


class StringFieldSize(str, Enum):
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"


@dataclass(frozen=True, kw_only=True)
class PasswordStoreChoice:
    password_id: str
    name: str


@dataclass(frozen=True, kw_only=True)
class I18nPassword:
    explicit_password: str
    password_store: str
    no_password_store_choices: str
    password_choice_invalid: str
    choose_password_from_store: str
    choose_password_type: str


class DictionaryGroupLayout(str, Enum):
    horizontal = "horizontal"
    vertical = "vertical"


@dataclass(frozen=True, kw_only=True)
class DictionaryGroup:
    key: Optional[str]
    title: Optional[str]
    help: Optional[str]
    layout: DictionaryGroupLayout


@dataclass(frozen=True, kw_only=True)
class SingleChoiceElement:
    name: str
    title: str


@dataclass(frozen=True, kw_only=True)
class MultipleChoiceElement:
    name: str
    title: str


@dataclass(frozen=True, kw_only=True)
class DualListChoiceI18n:
    add: str
    remove: str
    add_all: str
    remove_all: str
    available_options: str
    selected_options: str
    selected: str
    no_elements_available: str
    no_elements_selected: str
    autocompleter_loading: str
    search_available_options: str
    search_selected_options: str
    and_x_more: str


class CascadingSingleChoiceLayout(str, Enum):
    vertical = "vertical"
    horizontal = "horizontal"
    button_group = "button_group"


@dataclass(frozen=True, kw_only=True)
class FileUploadI18n:
    replace_file: str


@dataclass(frozen=True, kw_only=True)
class CommentTextAreaI18n:
    prefix_date_and_comment: str


class ConnectorType(str, Enum):
    microsoft_entra_id = "microsoft_entra_id"


@dataclass(frozen=True, kw_only=True)
class AuthorityUrls:
    base_url: str


@dataclass(frozen=True, kw_only=True)
class Authority:
    authority_id: Optional[str] = None
    authority_name: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class MetricBackendAttribute:
    key: str
    value: str


type MetricBackendAttributes = Sequence[MetricBackendAttribute]


@dataclass(frozen=True, kw_only=True)
class MetricI18n:
    host_input_hint: str
    host_filter: str
    service_input_hint: str
    service_filter: str


@dataclass(frozen=True, kw_only=True)
class DataSizeI18n:
    choose_unit: str


@dataclass(frozen=True, kw_only=True)
class Locked:
    message: str


@dataclass(frozen=True, kw_only=True)
class TimeSpanI18n:
    millisecond: str
    second: str
    minute: str
    hour: str
    day: str
    validation_negative_number: str


class TimeSpanTimeMagnitude(str, Enum):
    millisecond = "millisecond"
    second = "second"
    minute = "minute"
    hour = "hour"
    day = "day"


class TupleLayout(str, Enum):
    horizontal_titles_top = "horizontal_titles_top"
    horizontal = "horizontal"
    vertical = "vertical"
    float = "float"


@dataclass(frozen=True, kw_only=True)
class I18nOptionalChoice:
    label: str
    none_label: str


@dataclass(frozen=True, kw_only=True)
class SingleChoiceEditableI18n:
    slidein_save_button: str
    slidein_cancel_button: str
    slidein_create_button: str
    slidein_new_title: str
    slidein_edit_title: str
    edit: str
    create: str
    loading: str
    no_objects: str
    no_selection: str
    validation_error: str
    fatal_error: str
    fatal_error_reload: str
    permanent_change_warning: str
    permanent_change_warning_dismiss: str


class FetchMethod(str, Enum):
    ajax_vs_autocomplete = "ajax_vs_autocomplete"
    rest_autocomplete = "rest_autocomplete"


@dataclass(frozen=True, kw_only=True)
class AutocompleterParams:
    show_independent_of_context: Optional[bool] = None
    strict: Optional[bool] = None
    escape_regex: Optional[bool] = None
    literal_search: Optional[bool] = None
    world: Optional[str] = None
    context: Optional[Mapping[str, Any]] = None
    input_hint: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class AutocompleterData:
    ident: str
    params: AutocompleterParams


@dataclass(frozen=True, kw_only=True)
class Autocompleter:
    data: AutocompleterData
    fetch_method: Optional[FetchMethod] = FetchMethod.ajax_vs_autocomplete


class ListOfStringsLayout(str, Enum):
    horizontal = "horizontal"
    vertical = "vertical"


@dataclass(frozen=True, kw_only=True)
class Condition:
    name: str
    title: str


@dataclass(frozen=True, kw_only=True)
class ConditionGroup:
    title: str
    conditions: Sequence[Condition]


@dataclass(frozen=True, kw_only=True)
class ConditionChoicesI18n:
    choose_operator: str
    choose_condition: str
    add_condition_label: str
    select_condition_group_to_add: str
    no_more_condition_groups_to_add: str
    eq_operator: str
    ne_operator: str
    or_operator: str
    nor_operator: str


@dataclass(frozen=True, kw_only=True)
class LabelsI18n:
    add_some_labels: str
    remove_label: str
    key_value_format_error: str
    uniqueness_error: str
    max_labels_reached: str


class LabelSource(str, Enum):
    explicit = "explicit"
    ruleset = "ruleset"
    discovered = "discovered"


@dataclass(frozen=True, kw_only=True)
class TimeSpecificI18n:
    enable: str
    disable: str


@dataclass(frozen=True, kw_only=True)
class ValidationMessage:
    location: Sequence[str]
    message: str
    replacement_value: Any


@dataclass(frozen=True, kw_only=True)
class Eq:
    oper_eq: str


@dataclass(frozen=True, kw_only=True)
class Ne:
    oper_ne: str


@dataclass(frozen=True, kw_only=True)
class Or:
    oper_or: Sequence[str]


@dataclass(frozen=True, kw_only=True)
class Nor:
    oper_nor: Sequence[str]


@dataclass(frozen=True, kw_only=True)
class ConditionChoicesValue:
    group_name: str
    value: Union[Eq, Ne, Or, Nor]


class BinaryConditionChoicesOperator(StrEnum):
    and_ = "and"
    or_ = "or"
    not_ = "not"


@dataclass(frozen=True, kw_only=True)
class BinaryConditionChoicesItem:
    operator: BinaryConditionChoicesOperator
    label: str


@dataclass(frozen=True, kw_only=True)
class BinaryConditionChoicesGroup:
    operator: BinaryConditionChoicesOperator
    label_group: Sequence[BinaryConditionChoicesItem]


type BinaryConditionChoicesValue = Sequence[BinaryConditionChoicesGroup]


type Values = Union[ConditionChoicesValue, BinaryConditionChoicesValue]


@dataclass(frozen=True, kw_only=True)
class FormSpec:
    title: str
    help: str
    validators: Sequence[Validator]


@dataclass(frozen=True, kw_only=True)
class Integer(FormSpec):
    label: Optional[str]
    unit: Optional[str]
    input_hint: Optional[str]
    type: Literal["integer"] = "integer"


@dataclass(frozen=True, kw_only=True)
class DatePicker(FormSpec):
    label: Optional[str]
    type: Literal["date_picker"] = "date_picker"


@dataclass(frozen=True, kw_only=True)
class TimePicker(FormSpec):
    label: Optional[str]
    type: Literal["time_picker"] = "time_picker"


@dataclass(frozen=True, kw_only=True)
class Float(FormSpec):
    label: Optional[str]
    unit: Optional[str]
    input_hint: Optional[str]
    type: Literal["float"] = "float"


@dataclass(frozen=True, kw_only=True)
class Regex(FormSpec):
    label: str
    input_type: str
    no_results_hint: str
    autocompleter: Autocompleter
    type: Literal["regex"] = "regex"


@dataclass(frozen=True, kw_only=True)
class LegacyValuespec(FormSpec):
    varprefix: str
    type: Literal["legacy_valuespec"] = "legacy_valuespec"


@dataclass(frozen=True, kw_only=True)
class String(FormSpec):
    label: Optional[str]
    input_hint: Optional[str]
    field_size: StringFieldSize
    autocompleter: Optional[Autocompleter]
    type: Literal["string"] = "string"


@dataclass(frozen=True, kw_only=True)
class Password(FormSpec):
    password_store_choices: Sequence[PasswordStoreChoice]
    i18n: I18nPassword
    type: Literal["password"] = "password"


@dataclass(frozen=True, kw_only=True)
class List(FormSpec):
    element_template: FormSpec
    element_default_value: Any
    editable_order: bool
    add_element_label: str
    remove_element_label: str
    no_element_label: str
    type: Literal["list"] = "list"


@dataclass(frozen=True, kw_only=True)
class DictionaryElement:
    name: str
    required: bool
    group: Optional[DictionaryGroup]
    default_value: Any
    render_only: bool
    parameter_form: FormSpec


@dataclass(frozen=True, kw_only=True)
class Dictionary(FormSpec):
    groups: Sequence[DictionaryGroup]
    no_elements_text: str
    additional_static_elements: Optional[Mapping[str, Any]]
    elements: Sequence[DictionaryElement] = field(default_factory=lambda: [])
    type: Literal["dictionary"] = "dictionary"


@dataclass(frozen=True, kw_only=True)
class TwoColumnDictionary(FormSpec):
    groups: Sequence[DictionaryGroup]
    no_elements_text: str
    additional_static_elements: Optional[Mapping[str, Any]]
    type: Literal["two_column_dictionary"] = "two_column_dictionary"
    elements: Optional[Sequence[DictionaryElement]] = field(default_factory=lambda: [])


@dataclass(frozen=True, kw_only=True)
class SingleChoice(FormSpec):
    no_elements_text: Optional[str]
    frozen: bool
    label: Optional[str]
    input_hint: Optional[str]
    type: Literal["single_choice"] = "single_choice"
    elements: Sequence[SingleChoiceElement] = field(default_factory=lambda: [])


@dataclass(frozen=True, kw_only=True)
class DualListChoice(FormSpec):
    i18n: DualListChoiceI18n
    elements: Optional[Sequence[MultipleChoiceElement]] = field(
        default_factory=lambda: []
    )
    show_toggle_all: Optional[bool] = False
    autocompleter: Optional[Autocompleter] = None
    type: Literal["dual_list_choice"] = "dual_list_choice"


@dataclass(frozen=True, kw_only=True)
class CheckboxListChoice(FormSpec):
    i18n: DualListChoiceI18n
    show_toggle_all: Any
    type: Literal["checkbox_list_choice"] = "checkbox_list_choice"
    elements: Optional[Sequence[MultipleChoiceElement]] = field(
        default_factory=lambda: []
    )


@dataclass(frozen=True, kw_only=True)
class CascadingSingleChoiceElement:
    name: str
    title: str
    default_value: Any
    parameter_form: FormSpec


@dataclass(frozen=True, kw_only=True)
class CascadingSingleChoice(FormSpec):
    no_elements_text: str
    label: Optional[str]
    input_hint: Optional[str]
    type: Literal["cascading_single_choice"] = "cascading_single_choice"
    elements: Sequence[CascadingSingleChoiceElement] = field(default_factory=lambda: [])
    layout: CascadingSingleChoiceLayout = CascadingSingleChoiceLayout.vertical


@dataclass(frozen=True, kw_only=True)
class FileUpload(FormSpec):
    i18n: FileUploadI18n
    type: Literal["file_upload"] = "file_upload"


@dataclass(frozen=True, kw_only=True)
class FixedValue(FormSpec):
    label: Optional[str]
    value: Any
    type: Literal["fixed_value"] = "fixed_value"


@dataclass(frozen=True, kw_only=True)
class BooleanChoice(FormSpec):
    label: Optional[str]
    text_on: str
    text_off: str
    type: Literal["boolean_choice"] = "boolean_choice"


@dataclass(frozen=True, kw_only=True)
class MultilineText(FormSpec):
    label: Optional[str]
    macro_support: bool
    monospaced: bool
    input_hint: Optional[str]
    type: Literal["multiline_text"] = "multiline_text"


@dataclass(frozen=True, kw_only=True)
class CommentTextArea(FormSpec):
    label: Optional[str]
    macro_support: bool
    monospaced: bool
    input_hint: Optional[str]
    user_name: str
    i18n: CommentTextAreaI18n
    type: Literal["comment_text_area"] = "comment_text_area"


@dataclass(frozen=True, kw_only=True)
class MicrosoftEntraIdUrls:
    global_: AuthorityUrls
    china: AuthorityUrls


@dataclass(frozen=True, kw_only=True)
class MetricBackendCustomQuery(FormSpec):
    metric_name: Optional[str]
    resource_attributes: MetricBackendAttributes
    scope_attributes: MetricBackendAttributes
    data_point_attributes: MetricBackendAttributes
    aggregation_lookback: float
    aggregation_histogram_percentile: float
    service_name_template: str
    type: Literal["metric_backend_custom_query"] = "metric_backend_custom_query"


@dataclass(frozen=True, kw_only=True)
class DcdMetricBackendFilter(FormSpec):
    resource_attributes: MetricBackendAttributes
    scope_attributes: MetricBackendAttributes
    data_point_attributes: MetricBackendAttributes
    type: Literal["dcd_metric_backend_filter"] = "dcd_metric_backend_filter"


@dataclass(frozen=True, kw_only=True)
class Metric(FormSpec):
    label: Optional[str]
    input_hint: Optional[str]
    field_size: StringFieldSize
    autocompleter: Optional[Autocompleter]
    service_filter_autocompleter: Autocompleter
    host_filter_autocompleter: Autocompleter
    i18n: MetricI18n
    type: Literal["metric"] = "metric"


@dataclass(frozen=True, kw_only=True)
class DataSize(FormSpec):
    label: Optional[str]
    displayed_magnitudes: Sequence[str]
    input_hint: Optional[str]
    i18n: DataSizeI18n
    type: Literal["data_size"] = "data_size"


@dataclass(frozen=True, kw_only=True)
class TopicElement:
    name: str
    required: bool
    parameter_form: FormSpec
    default_value: Any
    type: Literal["topic_element"] = "topic_element"


@dataclass(frozen=True, kw_only=True)
class TimeSpan(FormSpec):
    label: Optional[str]
    i18n: TimeSpanI18n
    displayed_magnitudes: Sequence[TimeSpanTimeMagnitude]
    input_hint: Optional[float]
    type: Literal["time_span"] = "time_span"


@dataclass(frozen=True, kw_only=True)
class OptionalChoice(FormSpec):
    parameter_form: FormSpec
    i18n: I18nOptionalChoice
    parameter_form_default_value: Any
    type: Literal["optional_choice"] = "optional_choice"


@dataclass(frozen=True, kw_only=True)
class SimplePassword(FormSpec):
    type: Literal["simple_password"] = "simple_password"


@dataclass(frozen=True, kw_only=True)
class SingleChoiceEditable(FormSpec):
    config_entity_type: str
    config_entity_type_specifier: str
    elements: Sequence[SingleChoiceElement]
    allow_editing_existing_elements: bool
    i18n: SingleChoiceEditableI18n
    type: Literal["single_choice_editable"] = "single_choice_editable"


@dataclass(frozen=True, kw_only=True)
class ListOfStrings(FormSpec):
    string_spec: FormSpec
    type: Literal["list_of_strings"] = "list_of_strings"
    string_default_value: Optional[str] = ""
    layout: Optional[ListOfStringsLayout] = ListOfStringsLayout.horizontal


@dataclass(frozen=True, kw_only=True)
class ConditionChoices(FormSpec):
    condition_groups: Mapping[str, ConditionGroup]
    i18n: ConditionChoicesI18n
    type: Literal["condition_choices"] = "condition_choices"


@dataclass(frozen=True, kw_only=True)
class BinaryConditionChoices(FormSpec):
    label: str
    autocompleter: Autocompleter
    type: Literal["binary_condition_choices"] = "binary_condition_choices"


@dataclass(frozen=True, kw_only=True)
class Labels(FormSpec):
    i18n: LabelsI18n
    autocompleter: Autocompleter
    max_labels: Optional[int]
    label_source: Optional[LabelSource]
    type: Literal["labels"] = "labels"


@dataclass(frozen=True, kw_only=True)
class TimeSpecific(FormSpec):
    i18n: TimeSpecificI18n
    parameter_form_enabled: FormSpec
    parameter_form_disabled: FormSpec
    type: Literal["time_specific"] = "time_specific"
    time_specific_values_key: Literal["tp_values"] = "tp_values"
    default_value_key: Literal["tp_default_value"] = "tp_default_value"


@dataclass(frozen=True, kw_only=True)
class ListUniqueSelection(FormSpec):
    element_template: Union[SingleChoice, CascadingSingleChoice]
    element_default_value: Any
    add_element_label: str
    remove_element_label: str
    no_element_label: str
    unique_selection_elements: Sequence[str]
    type: Literal["list_unique_selection"] = "list_unique_selection"


@dataclass(frozen=True, kw_only=True)
class Oauth2Urls:
    redirect: str
    back: str
    microsoft_entra_id: MicrosoftEntraIdUrls
    site_redirect_urls: Mapping[str, str]


@dataclass(frozen=True, kw_only=True)
class TopicGroup:
    title: str
    elements: Sequence[TopicElement]
    type: Literal["topic_group"] = "topic_group"


@dataclass(frozen=True, kw_only=True)
class Topic:
    name: str
    title: str
    elements: Union[Sequence[TopicGroup], Sequence[TopicElement]]
    locked: Optional[Locked]


@dataclass(frozen=True, kw_only=True)
class Catalog(FormSpec):
    elements: Sequence[Topic]
    type: Literal["catalog"] = "catalog"


@dataclass(frozen=True, kw_only=True)
class Oauth2ConnectionConfig:
    urls: Oauth2Urls


@dataclass(frozen=True, kw_only=True)
class Oauth2ConnectionSetup(FormSpec):
    config: Oauth2ConnectionConfig
    form_spec: FormSpec
    authority_mapping: Sequence[Authority]
    connector_type: ConnectorType
    type: Literal["oauth2_connection_setup"] = "oauth2_connection_setup"
    ident: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class VueFormspecComponents:
    components: Optional[Components] = None
    validation_message: Optional[ValidationMessage] = None
    values: Optional[Values] = None


type Components = Union[
    Integer,
    Float,
    Regex,
    String,
    Dictionary,
    TwoColumnDictionary,
    List,
    ListUniqueSelection,
    LegacyValuespec,
    SingleChoice,
    CascadingSingleChoice,
    FixedValue,
    BooleanChoice,
    MultilineText,
    CommentTextArea,
    Password,
    DataSize,
    Catalog,
    DualListChoice,
    CheckboxListChoice,
    TimeSpan,
    MetricBackendCustomQuery,
    DcdMetricBackendFilter,
    Oauth2ConnectionSetup,
    Metric,
    SingleChoiceEditable,
    Tuple,
    OptionalChoice,
    SimplePassword,
    ListOfStrings,
    ConditionChoices,
    BinaryConditionChoices,
    Labels,
    FileUpload,
    TimeSpecific,
    DatePicker,
    TimePicker,
]


@dataclass(frozen=True, kw_only=True)
class Tuple(FormSpec):
    elements: Sequence[Components]
    show_titles: bool
    type: Literal["tuple"] = "tuple"
    layout: TupleLayout = TupleLayout.vertical
