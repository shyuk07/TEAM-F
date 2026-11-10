export type TabBarHandle = { tabBar: true };

export const TAB_BAR_HANDLE: TabBarHandle = { tabBar: true };

export function isTabBarHandle(h: unknown): h is TabBarHandle {
  return typeof h === 'object' && h !== null && 'tabBar' in h && h.tabBar === true;
}
