// Barrel exports for the DClaw design-kit component library.
//
// Convention: import from `@/components/dk` rather than individual files.
//   import { DkButton, DkCard, DkInput } from "@/components/dk";
//
// New product UI MUST use these primitives. The shadcn-shaped components
// in `@/components/ui/*` exist only for legacy compatibility with the
// pre-v0.1 pages and will be retired as Phase 0.5 lands.

export { DkButton, type DkButtonProps } from "./button";
export {
  DkCard,
  DkCardHeader,
  DkCardTitle,
  DkCardDescription,
  DkCardContent,
  DkCardFooter,
} from "./card";
export { DkEyebrow } from "./eyebrow";
export { DkChip, type DkChipProps } from "./chip";
export { DkBadge, type DkBadgeProps } from "./badge";
export { DkAvatar, type DkAvatarProps } from "./avatar";
export { DkSkeleton } from "./skeleton";
export { DkProgress, type DkProgressProps } from "./progress";

export { DkInput, type DkInputProps } from "./input";
export { DkTextarea, type DkTextareaProps } from "./textarea";
export { DkLabel, type DkLabelProps } from "./label";
export { DkSelect, type DkSelectProps } from "./select";
export { DkSwitch, type DkSwitchProps } from "./switch";
export { DkCheckbox, type DkCheckboxProps } from "./checkbox";
export {
  DkRadio,
  DkRadioGroup,
  type DkRadioProps,
  type DkRadioGroupProps,
} from "./radio";
export { DkSlider, type DkSliderProps } from "./slider";

export {
  DkDialog,
  DkDialogHeader,
  DkDialogContent,
  DkDialogFooter,
  type DkDialogProps,
} from "./dialog";
export {
  DkTabs,
  DkTabsList,
  DkTabsTrigger,
  DkTabsContent,
} from "./tabs";
export {
  DkTable,
  DkTableHeader,
  DkTableBody,
  DkTableRow,
  DkTableHead,
  DkTableCell,
} from "./table";
export { DkPageHeader, type DkPageHeaderProps } from "./page-header";
export { DkEmptyState, type DkEmptyStateProps } from "./empty-state";
export {
  DkBreadcrumb,
  type DkBreadcrumbItem,
  type DkBreadcrumbProps,
} from "./breadcrumb";
export {
  DkSidebar,
  type DkSidebarItem,
  type DkSidebarGroup,
  type DkSidebarProps,
} from "./sidebar";
export { DkToastProvider, useDkToast } from "./toast";
export { DkOrgSwitcher } from "./org-switcher";
