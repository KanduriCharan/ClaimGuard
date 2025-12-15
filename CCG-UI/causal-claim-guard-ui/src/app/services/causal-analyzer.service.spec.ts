import { TestBed } from '@angular/core/testing';

import { CausalAnalyzerService } from './causal-analyzer.service';

describe('CausalAnalyzerService', () => {
  let service: CausalAnalyzerService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(CausalAnalyzerService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
