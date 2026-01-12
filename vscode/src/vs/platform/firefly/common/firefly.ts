/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *--------------------------------------------------------------------------------------------*/

import { createDecorator } from '../../instantiation/common/instantiation.js';
import { Event } from '../../../base/common/event.js';

export const IFireflyMainService = createDecorator<IFireflyMainService>('fireflyMainService');

export interface IFireflyStatus {
    readonly agentRunning: boolean;
    readonly currentThought?: string;
    readonly totalCost: number;
    readonly isAutonomous: boolean;
}

export interface IFireflyMainService {
    readonly _serviceBrand: undefined;

    readonly onDidChangeStatus: Event<IFireflyStatus>;

    getStatus(): IFireflyStatus;
    reloadAgent(): Promise<void>;
    setAutonomousMode(enabled: boolean): void;
    sendIntent(id: string, args: any[]): void;
    createAgent(name: string, persona: string): Promise<string>;
    deleteAgent(id: string): Promise<void>;

    // Phase 5: Safety & Model Controls
    setSafetyMode(mode: string): void;
    setActiveModel(modelId: string): void;
    sendChat(text: string): void;
}
