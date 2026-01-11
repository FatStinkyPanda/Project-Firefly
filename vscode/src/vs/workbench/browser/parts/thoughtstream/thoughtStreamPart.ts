/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See License.txt in the project root for license information.
 *--------------------------------------------------------------------------------------------*/

import './media/thoughtstreampart.css';
import { Part } from '../../part.js';
import { IThemeService } from '../../../../platform/theme/common/themeService.js';
import { IStorageService } from '../../../../platform/storage/common/storage.js';
import { IWorkbenchLayoutService, Parts } from '../../../services/layout/browser/layoutService.js';
import { IFireflyWorkbenchService } from '../../../services/firefly/common/firefly.js';
import { $ } from '../../../../base/browser/dom.js';

export class ThoughtStreamPart extends Part {

    static readonly HEIGHT = 35;

    get minimumWidth(): number { return 0; }
    get maximumWidth(): number { return 300; }
    get minimumHeight(): number { return ThoughtStreamPart.HEIGHT; }
    get maximumHeight(): number { return ThoughtStreamPart.HEIGHT; }

    private iconElement: HTMLElement | undefined;
    private textElement: HTMLElement | undefined;
    private costElement: HTMLElement | undefined;
    private modeElement: HTMLElement | undefined;

    constructor(
        @IThemeService themeService: IThemeService,
        @IStorageService storageService: IStorageService,
        @IWorkbenchLayoutService layoutService: IWorkbenchLayoutService,
        @IFireflyWorkbenchService private readonly fireflyService: IFireflyWorkbenchService
    ) {
        super(Parts.THOUGHTSTREAM_PART, { hasTitle: false }, themeService, storageService, layoutService);

        this._register(this.fireflyService.onDidChangeThought(thought => {
            if (this.textElement) {
                this.textElement.textContent = thought.text;
            }
        }));

        this._register(this.fireflyService.onDidChangeMode(mode => {
            if (this.modeElement) {
                this.modeElement.textContent = mode ? 'AUTONOMOUS' : 'INTERACTIVE';
                this.modeElement.classList.toggle('autonomous', mode);
            }

            // Apply global overlay class to the workbench
            const container = this.layoutService.getContainer((window as any).vscodeWindowId ? window : (window as any).mainWindow);
            if (container) {
                container.classList.toggle('firefly-autonomous-mode', mode);
            }
        }));
    }

    protected override createContentArea(parent: HTMLElement): HTMLElement {
        this.element = parent;

        this.iconElement = $('.thought-icon');
        this.element.appendChild(this.iconElement);

        const label = $('.thought-label');
        label.textContent = 'Firefly Thinking';
        this.element.appendChild(label);

        this.textElement = $('.thought-text');
        this.textElement.textContent = 'Awaiting instructions...';
        this.element.appendChild(this.textElement);

        this.modeElement = $('.thought-mode');
        this.modeElement.textContent = 'IDLE';
        this.element.appendChild(this.modeElement);

        this.costElement = $('.thought-cost');
        this.costElement.textContent = '$0.00000';
        this.element.appendChild(this.costElement);

        return this.element;
    }

    override layout(width: number, height: number): void {
        super.layoutContents(width, height);
    }

    toJSON(): object {
        return {
            type: 'workbench.parts.thoughtstream'
        };
    }
}
