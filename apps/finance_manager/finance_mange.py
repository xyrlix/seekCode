import json
from datetime import datetime, date
from typing import List, Dict, Optional


class Transaction:
    """交易记录类"""

    def __init__(self, amount: float, category: str, description: str,
                 transaction_type: str, date_str: str = None):
        self.amount = abs(amount)  # 金额总是正数
        self.category = category
        self.description = description
        self.type = transaction_type  # 'income' 或 'expense'
        self.date = date_str or datetime.now().strftime('%Y-%m-%d')
        self.id = self._generate_id()

    def _generate_id(self) -> str:
        """生成唯一 ID"""
        return f"{self.type}_{self.date}_{hash(self.description) % 10000:04d}"

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'id': self.id,
            'amount': self.amount,
            'category': self.category,
            'description': self.description,
            'type': self.type,
            'date': self.date
        }

    @classmethod
    def from_dict(cls, data: Dict):
        """从字典创建对象"""
        transaction = cls(
            amount=data['amount'],
            category=data['category'],
            description=data['description'],
            transaction_type=data['type'],
            date_str=data['date']
        )
        transaction.id = data['id']
        return transaction

    def __str__(self) -> str:
        sign = '+' if self.type == 'income' else '-'
        return f"{self.date} | {sign}¥{self.amount:.2f} | {self.category} | {self.description}"


class FinanceManager:
    """财务管理器"""

    def __init__(self, data_file: str = 'finance_data.json'):
        self.data_file = data_file
        self.transactions: List[Transaction] = []
        self.categories = {
            'income': ['工资', '奖金', '投资收益', '其他收入'],
            'expense': ['餐饮', '交通', '购物', '娱乐', '医疗', '教育', '其他支出']
        }
        self.load_data()

    def add_transaction(self, amount: float, category: str, description: str,
                        transaction_type: str, date_str: str = None) -> bool:
        """添加交易记录"""
        try:
            # 验证输入
            if amount <= 0:
                print("金额必须大于 0")
                return False

            if transaction_type not in ['income', 'expense']:
                print("交易类型必须是 'income' 或 'expense'")
                return False

            if category not in self.categories[transaction_type]:
                print(f"无效的类别。可选类别: {', '.join(self.categories[transaction_type])}")
                return False

            # 创建交易记录
            transaction = Transaction(amount, category, description, transaction_type, date_str)
            self.transactions.append(transaction)

            print(f"成功添加{'收入' if transaction_type == 'income' else '支出'}记录: ¥{amount:.2f}")
            self.save_data()
            return True
        except Exception as e:
            print(f"添加交易记录失败: {e}")
            return False

    def get_transactions(self, start_date: str = None, end_date: str = None,
                         category: str = None, transaction_type: str = None) -> List[Transaction]:
        """查询交易记录"""
        filtered_transactions = self.transactions.copy()

        # 按日期过滤
        if start_date:
            filtered_transactions = [t for t in filtered_transactions if t.date >= start_date]
        if end_date:
            filtered_transactions = [t for t in filtered_transactions if t.date <= end_date]

        # 按类别过滤
        if category:
            filtered_transactions = [t for t in filtered_transactions if t.category == category]

        # 按类型过滤
        if transaction_type:
            filtered_transactions = [t for t in filtered_transactions if t.type == transaction_type]

        return filtered_transactions

    def delete_transaction(self, transaction_id: str) -> bool:
        """删除交易记录"""
        for i, transaction in enumerate(self.transactions):
            if transaction.id == transaction_id:
                deleted = self.transactions.pop(i)
                print(f"成功删除交易记录: {deleted}")
                self.save_data()
                return True

        print(f"未找到 ID 为 {transaction_id} 的交易记录")
        return False

    def get_balance(self) -> float:
        """获取当前余额"""
        total_income = sum(t.amount for t in self.transactions if t.type == 'income')
        total_expense = sum(t.amount for t in self.transactions if t.type == 'expense')
        return total_income - total_expense

    def get_monthly_summary(self, year: int, month: int) -> Dict:
        """获取月度汇总"""
        month_str = f"{year:04d}-{month:02d}"
        monthly_transactions = [t for t in self.transactions if t.date.startswith(month_str)]

        income_total = sum(t.amount for t in monthly_transactions if t.type == 'income')
        expense_total = sum(t.amount for t in monthly_transactions if t.type == 'expense')

        # 按类别统计
        income_by_category = {}
        expense_by_category = {}

        for transaction in monthly_transactions:
            if transaction.type == 'income':
                income_by_category[transaction.category] = \
                income_by_category.get(transaction.category, 0) + transaction.amount
            else:
                expense_by_category[transaction.category] = \
                expense_by_category.get(transaction.category, 0) + transaction.amount

        return {
            'year': year,
            'month': month,
            'income_total': income_total,
            'expense_total': expense_total,
            'net_income': income_total - expense_total,
            'income_by_category': income_by_category,
            'expense_by_category': expense_by_category,
            'transaction_count': len(monthly_transactions)
        }

    def generate_report(self, start_date: str = None, end_date: str = None) -> None:
        """生成财务报告"""
        transactions = self.get_transactions(start_date, end_date)

        if not transactions:
            print("指定期间内没有交易记录")
            return

        # 基本统计
        total_income = sum(t.amount for t in transactions if t.type == 'income')
        total_expense = sum(t.amount for t in transactions if t.type == 'expense')
        net_income = total_income - total_expense

        print("\n" + "=" * 50)
        print("财务报告")
        print("=" * 50)

        if start_date and end_date:
            print(f"报告期间: {start_date} 至 {end_date}")
        elif start_date:
            print(f"报告期间: {start_date} 至今")
        elif end_date:
            print(f"报告期间: 开始 至 {end_date}")
        else:
            print("报告期间: 全部记录")

        print(f"\n 基本统计:")
        print(f" 总收入: ¥{total_income:,.2f}")
        print(f" 总支出: ¥{total_expense:,.2f}")
        print(f" 净收入: ¥{net_income:,.2f}")
        print(f" 交易笔数: {len(transactions)}")

        # 收入分类统计
        income_by_category = {}
        expense_by_category = {}

        for transaction in transactions:
            if transaction.type == 'income':
                income_by_category[transaction.category] = \
                income_by_category.get(transaction.category, 0) + transaction.amount
            else:
                expense_by_category[transaction.category] = \
                expense_by_category.get(transaction.category, 0) + transaction.amount

        if income_by_category:
            print(f"\n 收入分类:")
            for category, amount in sorted(income_by_category.items(), key=lambda x: x[1], reverse=True):
                percentage = (amount / total_income) * 100 if total_income > 0 else 0
                print(f" {category}: ¥{amount:,.2f} ({percentage:.1f}%)")

        if expense_by_category:
            print(f"\n 支出分类:")
            for category, amount in sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True):
                percentage = (amount / total_expense) * 100 if total_expense > 0 else 0
                print(f" {category}: ¥{amount:,.2f} ({percentage:.1f}%)")

        # 最大单笔交易
        if transactions:
            max_income = max([t for t in transactions if t.type == 'income'],
                            key=lambda x: x.amount, default=None)
            max_expense = max([t for t in transactions if t.type == 'expense'],
                            key=lambda x: x.amount, default=None)

        print(f"\n 最大单笔交易:")
        if max_income:
            print(f" 最大收入: ¥{max_income.amount:.2f} ({max_income.description})")
        if max_expense:
            print(f" 最大支出: ¥{max_expense.amount:.2f} ({max_expense.description})")

    def save_data(self) -> None:
        """保存数据到文件"""
        try:
            data = [transaction.to_dict() for transaction in self.transactions]
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存数据失败: {e}")

    def load_data(self) -> None:
        """从文件加载数据"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.transactions = [Transaction.from_dict(item) for item in data]
                print(f"成功加载 {len(self.transactions)} 条交易记录")
        except FileNotFoundError:
            print("数据文件不存在，将创建新文件")
            self.transactions = []
        except Exception as e:
            print(f"加载数据失败: {e}")
            self.transactions = []

    def display_transactions(self, limit: int = 10) -> None:
        """显示最近的交易记录"""
        if not self.transactions:
            print("暂无交易记录")
            return

        print(f"\n 最近 {min(limit, len(self.transactions))} 条交易记录:")
        print("-" * 70)

        # 按日期排序，最新的在前
        sorted_transactions = sorted(self.transactions,
                                    key=lambda x: x.date, reverse=True)

        for transaction in sorted_transactions[:limit]:
            print(transaction)


def main():
    """主程序"""
    manager = FinanceManager()

    # 添加示例数据
    print("=== 个人财务管理器演示 ===")

    # 添加一些示例交易
    manager.add_transaction(5000, '工资', '月工资', 'income', '2025-01-01')
    manager.add_transaction(800, '餐饮', '聚餐', 'expense', '2025-01-02')
    manager.add_transaction(200, '交通', '地铁卡充值', 'expense', '2025-01-03')
    manager.add_transaction(1500, '奖金', '项目奖金', 'income', '2025-01-05')
    manager.add_transaction(300, '购物', '买衣服', 'expense', '2025-01-06')
    manager.add_transaction(150, '娱乐', '看电影', 'expense', '2025-01-07')

    # 显示交易记录
    manager.display_transactions()

    # 显示当前余额
    print(f"\n 当前余额: ¥{manager.get_balance():.2f}")

    # 生成月度汇总
    summary = manager.get_monthly_summary(2025, 1)
    print(f"\n2025 年 1 月汇总:")
    print(f" 收入: ¥{summary['income_total']:.2f}")
    print(f" 支出: ¥{summary['expense_total']:.2f}")
    print(f" 净收入: ¥{summary['net_income']:.2f}")

    # 生成财务报告
    manager.generate_report('2025-01-01', '2025-01-31')


if __name__ == "__main__":
    main()
