"""
Main Pipeline Orchestrator for Demand Zone ML Trading
Runs the complete automated pipeline from data generation to model evaluation
"""

import os
import sys
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Import modules
from generate_ml_dataset import DemandZoneDatasetGenerator, CONFIG
from ml_demand_zone_trainer import DemandZoneMLTrainer


class PipelineOrchestrator:
    """
    Main orchestrator for the complete ML trading pipeline
    """
    
    def __init__(self):
        """Initialize pipeline"""
        self.start_time = datetime.now()
        self.results = {}
        
    def log(self, message: str):
        """Print log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def step_1_generate_dataset(self):
        """Step 1: Generate ML dataset from stock CSV files"""
        print("\n" + "=" * 60)
        print("STEP 1: Generate ML Dataset")
        print("=" * 60)
        
        # Check if data folder exists
        if not os.path.exists(CONFIG['data_folder']):
            self.log(f"ERROR: Data folder '{CONFIG['data_folder']}' not found")
            self.log(f"Please create the folder and add stock CSV files (e.g., AMC_data.csv)")
            return False
        
        # Initialize generator
        generator = DemandZoneDatasetGenerator()
        
        # Generate dataset
        try:
            dataset = generator.generate_dataset()
            
            if len(dataset) == 0:
                self.log("ERROR: No dataset generated. Check your stock CSV files.")
                return False
            
            # Save dataset
            generator.save_dataset(dataset)
            
            self.results['dataset_size'] = len(dataset)
            self.results['zones_found'] = generator.total_zones_found
            
            self.log(f"✓ Dataset generated successfully: {len(dataset)} signals")
            self.log(f"✓ Total zones found: {generator.total_zones_found}")
            
            return True
            
        except Exception as e:
            self.log(f"ERROR: Dataset generation failed: {str(e)}")
            return False
    
    def step_2_train_models(self):
        """Step 2: Train ML models"""
        print("\n" + "=" * 60)
        print("STEP 2: Train ML Models")
        print("=" * 60)
        
        # Check if dataset exists
        if not os.path.exists(CONFIG['output_file']):
            self.log(f"ERROR: Dataset file '{CONFIG['output_file']}' not found")
            self.log("Please run Step 1 first to generate the dataset")
            return False
        
        # Initialize trainer
        trainer = DemandZoneMLTrainer(dataset_path=CONFIG['output_file'])
        
        try:
            # Run full pipeline with model comparison
            self.log("Training and comparing models (Random Forest, XGBoost, LightGBM)...")
            metrics = trainer.run_full_pipeline(
                target_col='hit_target',
                use_risk_adjusted=False,
                compare_models_flag=True
            )
            
            self.results['metrics'] = metrics
            self.log("✓ Model training completed")
            
            return True
            
        except Exception as e:
            self.log(f"ERROR: Model training failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def step_3_evaluate_performance(self):
        """Step 3: Evaluate performance"""
        print("\n" + "=" * 60)
        print("STEP 3: Evaluate Performance")
        print("=" * 60)
        
        if 'metrics' not in self.results:
            self.log("ERROR: No metrics available. Run Step 2 first.")
            return False
        
        metrics = self.results['metrics']
        
        self.log("Model Performance Metrics:")
        self.log(f"  Precision: {metrics.get('precision', 0):.4f}")
        self.log(f"  Recall: {metrics.get('recall', 0):.4f}")
        self.log(f"  F1 Score: {metrics.get('f1', 0):.4f}")
        self.log(f"  ROC-AUC: {metrics.get('auc', 0):.4f}")
        
        self.log("✓ Performance evaluation completed")
        
        return True
    
    def step_4_save_results(self):
        """Step 4: Save results"""
        print("\n" + "=" * 60)
        print("STEP 4: Save Results")
        print("=" * 60)
        
        # Save results summary
        results_file = 'pipeline_results.txt'
        
        with open(results_file, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("Demand Zone ML Trading Pipeline Results\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Run Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("Dataset Statistics:\n")
            f.write(f"  Total Signals: {self.results.get('dataset_size', 0)}\n")
            f.write(f"  Zones Found: {self.results.get('zones_found', 0)}\n\n")
            
            if 'metrics' in self.results:
                metrics = self.results['metrics']
                f.write("Model Performance:\n")
                f.write(f"  Precision: {metrics.get('precision', 0):.4f}\n")
                f.write(f"  Recall: {metrics.get('recall', 0):.4f}\n")
                f.write(f"  F1 Score: {metrics.get('f1', 0):.4f}\n")
                f.write(f"  ROC-AUC: {metrics.get('auc', 0):.4f}\n\n")
                f.write(f"  Probability Threshold: {metrics.get('threshold', 0.5):.2f}\n\n")

                trading = metrics.get('trading')
                if trading:
                    f.write("Trading Performance (held-out test set):\n")
                    f.write(f"  Trades Taken: {trading.get('num_trades', 0)}\n")
                    f.write(f"  Total Return: {trading.get('total_return', 0):.2%}\n")
                    f.write(f"  Max Drawdown: {trading.get('max_drawdown', 0):.2%}\n")
                    f.write(f"  Profit Factor: {trading.get('profit_factor', 0):.2f}\n\n")

                ranking = metrics.get('return_ranking')
                if ranking:
                    f.write("Forward-Return Ranking (held-out test set):\n")
                    f.write(f"  MAE: {ranking.get('mae', 0):.4f}\n")
                    f.write(f"  R-squared: {ranking.get('r2', 0):.4f}\n")
                    f.write(f"  Spearman Rank Correlation: {ranking.get('spearman_rank_correlation', 0):.4f}\n\n")

                sub_10 = metrics.get('sub_10_test')
                if sub_10:
                    f.write("Sub-$10 Classification (held-out test subset):\n")
                    f.write(f"  Precision: {sub_10.get('precision', 0):.4f}\n")
                    f.write(f"  Recall: {sub_10.get('recall', 0):.4f}\n")
                    f.write(f"  ROC-AUC: {sub_10.get('auc', 0):.4f}\n\n")
        
        self.log(f"✓ Results saved to {results_file}")
        
        return True
    
    def run(self):
        """Run the complete pipeline"""
        print("\n" + "=" * 60)
        print("DEMAND ZONE ML TRADING PIPELINE")
        print("=" * 60)
        print(f"Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run steps
        success = True
        
        # Step 1: Generate dataset
        if not self.step_1_generate_dataset():
            success = False
        
        # Step 2: Train models (only if Step 1 succeeded)
        if success:
            if not self.step_2_train_models():
                success = False
        
        # Step 3: Evaluate performance (only if Step 2 succeeded)
        if success:
            if not self.step_3_evaluate_performance():
                success = False
        
        # Step 4: Save results
        if success:
            self.step_4_save_results()
        
        # Final summary
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        print("\n" + "=" * 60)
        if success:
            print("PIPELINE COMPLETED SUCCESSFULLY")
        else:
            print("PIPELINE COMPLETED WITH ERRORS")
        print("=" * 60)
        print(f"Duration: {duration}")
        print(f"Ended at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return success


def main():
    """Main execution function"""
    # Create orchestrator
    orchestrator = PipelineOrchestrator()
    
    # Run pipeline
    success = orchestrator.run()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
