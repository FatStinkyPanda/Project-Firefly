/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *--------------------------------------------------------------------------------------------*/

import { createDecorator } from '../../../../platform/instantiation/common/instantiation.js';
import { Event } from '../../../../base/common/event.js';

export const IFireflyWorkbenchService = createDecorator<IFireflyWorkbenchService>('fireflyWorkbenchService');

export interface IFireflyThought {
    readonly text: string;
    readonly type: 'reasoning' | 'action' | 'observation';
}

export interface IFireflyWorkbenchService {
    readonly _serviceBrand: undefined;

    readonly onDidChangeThought: Event<IFireflyThought>;
    readonly onDidChangeMode: Event<boolean>;
    readonly onDidChangeStatus: Event<void>;

    isAutonomousMode(): boolean;
    setAutonomousMode(enabled: boolean): void;

    getCurrentThought(): IFireflyThought | undefined;
    getTotalCost(): number;

    /**
     * Allows the workbench to report user intents directly to Firefly
     */
    reportIntent(id: string, args: unknown[]): void;
}
