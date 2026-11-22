import unittest
from counter_alert import CounterMonitor

class CounterTests(unittest.TestCase):
    def test_wait_and_cooldown(self):
        c = CounterMonitor(wait_seconds=25,cooldown_seconds=60,min_samples=2)
        self.assertFalse(c.evaluate('store:counter',1,0,0)['should_alert'])
        self.assertTrue(c.evaluate('store:counter',1,0,26)['should_alert'])
        self.assertFalse(c.evaluate('store:counter',1,0,35)['should_alert'])
        self.assertFalse(c.evaluate('store:counter',1,1,50)['should_alert'])
        self.assertFalse(c.evaluate('store:counter',1,0,80)['should_alert'])
        self.assertTrue(c.evaluate('store:counter',1,0,106)['should_alert'])
    def test_new_key_and_no_customers(self):
        c = CounterMonitor(wait_seconds=20)
        self.assertEqual(c.evaluate('store:a',0,0,0)['state'],'clear_or_attended')
        self.assertEqual(c.evaluate('store:b',1,0,0)['state'],'observing')
        with self.assertRaises(ValueError):c.evaluate('store:b',-1,0,1)

if __name__=='__main__':unittest.main()
