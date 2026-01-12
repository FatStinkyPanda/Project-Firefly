/*---------------------------------------------------------------------------------------------
 *  Stub type declaration for @vscode/windows-registry
 *  This module is optional and only used on Windows for registry access
 *--------------------------------------------------------------------------------------------*/

declare module '@vscode/windows-registry' {
    export function GetStringRegKey(hive: string, path: string, name: string): string | undefined;
}
